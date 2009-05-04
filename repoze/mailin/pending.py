import os
import sqlite3

from zope.interface import implements

from repoze.mailin.interfaces import IPendingQueue

class PendingQueue(object):
    """ SQLite implementation of IPendingQueue.
    """
    implements(IPendingQueue)

    def __init__(self, path=None, dbfile=None, isolation_level=None):

        self.path = path

        if path is None:
            dbfile = ':memory:'

        if dbfile is None:
            dbfile = os.path.join(path, 'pending.db')

        sql = self.sql = sqlite3.connect(dbfile,
                                         isolation_level=isolation_level)

        found = sql.execute('select * from sqlite_master '
                             'where type = "table" and name = "pending"'
                           ).fetchall()
        if not found:
            sql.execute('create table pending'
                        '( id integer primary key'
                        ', message_id varchar(1024) unique'
                        ')')

    def push(self, message_id):
        """ See IPendingQueue.
        """
        self.sql.execute('insert into pending(message_id) '
                         'values("%s")' % message_id)

    def pop(self, how_many=1):
        """ See IPendingQueue.
        """
        cursor = self.sql.execute('select id, message_id from pending '
                                 'order by id')
        rows = cursor.fetchmany(how_many)
        cursor.close()
        count = 0
        popped = []
        while count < how_many:
            if not rows:
                break
            id, m_id = rows.pop(0)
            yield m_id
            popped.append(str(id))
            count += 1
        set = ','.join(['"%s"' % x for x in popped])
        self.sql.execute('delete from pending where id in (%s)' % set)

    def remove(self, message_id):
        """ See IPendingQueue.
        """
        cursor = self.sql.execute('delete from pending '
                                  'where message_id = "%s"' % message_id)
        if cursor.rowcount == 0:
            raise KeyError(message_id)

    def __nonzero__(self):
        """ See IPendingQueue.
        """
        return self.sql.execute('select count(*) from pending').fetchone()[0]

    def __iter__(self):
        return self.sql.execute('select id, message_id from pending ')

    def __del__(self):
        self.sql.close()
        del self.sql
