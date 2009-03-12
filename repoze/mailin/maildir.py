import mailbox
import os
import sqlite3
try:
    from email.utils import parsedate
except ImportError: # Python < 2.6
    from email.Utils import parsedate

from zope.interface import implements

from repoze.mailin.interfaces import IMessageStore
from repoze.mailin.interfaces import IPendingQueue

class MaildirStore:
    """ Use a :class:`mailbox.Maildir` to store messges.

    - Keeps metadata about messages in a SQLIte database, stored in
      the same directory (by default) as the ``Maildir``.

    - Messages may be delivered to the ``Maildir`` by external programs.
      While such messages are not part of the set managed by our
      ``IMessageStore`` API, they can be moved into the store via our
      :method:`drainInbox` method.

    - Messages stored via the ``IMessageStore`` API will be seated into
      folders keyed by year, month, and day of the message's ``Date`` field.
    """
    implements(IMessageStore)

    def __init__(self, path, dbfile=None, isolation_level=None):
        self.path = path
        self.mdpath = os.path.join(path, 'Maildir')
        if dbfile is None:
            dbfile = os.path.join(path, 'metadata.db')
        sql = self.sql = sqlite3.connect(dbfile,
                                         isolation_level=isolation_level)
        found = sql.execute('select * from sqlite_master '
                             'where type = "table" and name = "messages"'
                           ).fetchall()
        if not found:
            sql.execute('create table messages'
                        '( id integer primary key'
                        ', message_id varchar(1024) unique'
                        ', year integer not null'
                        ', month integer not null'
                        ', day integer not null'
                        ', maildir_key varchar(1024) not null unique'
                        ')')

 
    def __getitem__(self, message_id):
        """ See IMessageStore.
        """
        found = self.sql.execute('select year, month, day, maildir_key '
                                 'from messages where message_id = "%s"'
                                    % message_id
                                ).fetchall()
        if not found:
            raise KeyError(message_id)

        yy, mm, dd, key = found[0]
        folder_name = self._getFolderName(yy, mm, dd)
        folder = self._getMaildir(folder_name, create=False)
        return folder[key]

    def __setitem__(self, message_id, message):
        """ See IMessageStore.
        """
        to_store = mailbox.MaildirMessage(message)
        date = to_store['Date']
        yy, mm, dd, hh, mt, ss, wd, jd, dst = parsedate(date)
        folder_name = self._getFolderName(yy, mm, dd)
        folder = self._getMaildir(folder_name)
        key = folder.add(to_store)
        try:
            self.sql.execute('insert into messages'
                             '(message_id, year, month, day, maildir_key) '
                             'values("%s", %d, %d, %d, "%s")'
                              % (message_id, yy, mm, dd, key)
                            )
        except:
            folder.remove(key)
            raise

    def iterkeys(self):
        """ See IMessageStore.
        """
        cursor = self.sql.execute('select message_id from messages')
        for row in cursor:
            yield row[0]

    def drainInbox(self, pending_queue=None, limit=None, dry_run=False):
        """ Drain any items from our inbox into the main store.

        - Process the messages in the order they were added to the maildir.

        - If 'pending_queue' is not None, call 'push' on it for each
          message drained, passing the message_id.

        - 'limit' must be a positive integer, or None.  If 'limit' is
           not None, drain no more than 'limit' messages.

        - If 'dry_run' is false, don't make any changes.

        - Return a generator of the message IDs drained.
        """
        count = 0
        md = self._getMaildir()
        keys = list(md.iterkeys())  # avoid mutating while iterating
        for key in sorted(keys):    # preserve order
            message = md.get_message(key)
            message_id = message['Message-ID']
            if not dry_run:
                self[message_id] = message
                md.remove(key)
            if not dry_run and pending_queue is not None:
                pending_queue.push(message_id)
            yield message_id
            count += 1
            if limit and count >= limit:
                break

    def _getFolderName(self, yy, mm, dd):
        return '%04d.%02d.%02d' % (yy, mm, dd)

    def _getMaildir(self, folder=None, create=True):
        root = md = mailbox.Maildir(self.mdpath, factory=None, create=create)
        if folder is not None:
            if folder not in root.list_folders():
                if not create:
                    raise KeyError(folder)
                root.add_folder(folder)
            md = root.get_folder(folder)
        return md
