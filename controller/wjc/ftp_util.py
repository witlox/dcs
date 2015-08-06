import logging
import os
import re
import datetime
from stat import S_ISDIR

MTIME_TOLERANCE = 3

def _walk_remote(sftp, path, top_down=True):
    try:
        res = sftp.listdir_attr(path)
    except IOError:
        res = []

    for stat in res:
        rfile = os.path.join(path, stat.filename)

        if not S_ISDIR(stat.st_mode):
            yield 'file', rfile, stat
        else:
            if top_down:
                yield 'dir', rfile, stat
                for res in _walk_remote(sftp, rfile, top_down=top_down):
                    yield res
            else:
                for res in _walk_remote(sftp, rfile, top_down=top_down):
                    yield res
                yield 'dir', rfile, None

def _walk_local(path, top_down=True):
    for path, dirs, files in os.walk(path, topdown=top_down):
        for file in files:
            file = os.path.join(path, file)
            yield 'file', file, os.stat(file)
        for dir in dirs:
            dir = os.path.join(path, dir)
            yield 'dir', dir, os.stat(dir)

def _walk(sftp, *args, **kwargs):
    remote = kwargs.pop('remote', False)
    if remote:
        return _walk_remote(sftp, *args, **kwargs)
    else:
        return _walk_local(*args, **kwargs)

def _makedirs_dst(sftp, path, remote=True, dry=False):
    if remote:
        paths = []
        while path not in ('/', ''):
            paths.insert(0, path)
            path = os.path.dirname(path)

        for path in paths:
            try:
                sftp.lstat(path)
            except Exception:
                if not dry:
                    sftp.mkdir(path)
    else:
        if not os.path.exists(path):
            if not dry:
                os.makedirs(path)

def _validate_src(rfile, include, exclude):
    for re_ in include:
        if not re_.search(rfile):
            return False
    for re_ in exclude:
        if re_.search(rfile):
            return False
    return True

def _validate_dst(sftp, dfile, src_stat, remote=True):
    if remote:
        try:
            dst_stat = sftp.lstat(dfile)
        except Exception:
            return
    else:
        if not os.path.exists(dfile):
            return
        dst_stat = os.stat(dfile)

    if abs(dst_stat.st_mtime - src_stat.st_mtime) > MTIME_TOLERANCE:
        logging.debug('%s modified time mismatch (source: %s, destination: %s)' % (dfile, datetime.utcfromtimestamp(src_stat.st_mtime), datetime.utcfromtimestamp(dst_stat.st_mtime)))
        return
    if dst_stat.st_size != src_stat.st_size:
        return
    return True

def _save(sftp, src, dst, src_stat, remote=True):
    if remote:
        sftp.put(src, dst)
        sftp.utime(dst, (int(src_stat.st_atime), int(src_stat.st_mtime)))
    else:
        sftp.get(src, dst)
        os.utime(dst, (int(src_stat.st_atime), int(src_stat.st_mtime)))

def _delete_dst(sftp, path, files, remote=True, dry=False):
    if remote:
        callables = {'file': sftp.remove, 'dir': sftp.rmdir}
    else:
        callables = {'file': os.remove, 'dir': os.rmdir}

    for type, file, stat in _walk(path, topdown=False, remote=remote):
        if file not in files[type]:
            if not dry:
                try:
                    callables[type](file)
                except Exception, e:
                    logging.warning('failed to remove %s: %s' % (file, str(e)))
                    continue

            logging.debug('removed %s' % file)

def _get_filters(filters):
    if not filters:
        return []
    return [re.compile(f) for f in filters]

def sync(sftp, src, dst, download=True, include=None, exclude=None, delete=False, dry=False):
    """Sync files and directories.
    :param sftp: initialized (ssh) sftp connection
    :param src: source directory
    :param dst: destination directory
    :param download: True to sync from a remote source to a local destination,
        else sync from a local source to a remote destination
    :param include: list of regex patterns the source files must match
    :param exclude: list of regex patterns the source files must not match
    :param delete: remove destination files and directories not present
        at source or filtered by the include/exclude patterns
    :param dry: dry run, don't actually delete, just output debug
    """
    include = _get_filters(include)
    exclude = _get_filters(exclude)

    if src.endswith('/') != dst.endswith('/'):
        dst = os.path.join(dst, os.path.basename(src.rstrip('/')))
    src = src.rstrip('/')
    re_base = re.compile(r'^%s/' % re.escape(src))
    if not src:
        src = '/'

    _makedirs_dst(sftp, dst, remote=not download, dry=dry)

    started = datetime.utcnow()
    total_size = 0
    dst_list = {'file': [], 'dir': []}

    for atype, xfile, stat in _walk(sftp, src, remote=download):
        file_ = re_base.sub('', xfile)
        if not _validate_src(file_, include, exclude):
            logging.debug('filtered %s' % xfile)
            continue

        dst_file = os.path.join(dst, file_)
        dst_list[atype].append(dst_file)

        if atype == 'dir':
            _makedirs_dst(sftp, dst_file, remote=not download, dry=dry)
        elif atype == 'file':
            if not _validate_dst(sftp, dst_file, stat, remote=not download):
                if not dry:
                    _save(sftp, xfile, dst_file, stat, remote=not download)
                total_size += stat.st_size
                logging.debug('copied %s to %s' % (xfile, dst_file))

    if delete:
        _delete_dst(sftp, dst, dst_list, remote=not download, dry=dry)

    logging.info('transferred %s bytes in %s' % (total_size, datetime.utcnow() - started))
