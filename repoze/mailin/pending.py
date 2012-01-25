import os
import sqlite3

from zope.interface import implements

from repoze.mailin.interfaces import IPendingQueue

class PendingQueue(object):
    """ SQLite implementation of IPendingQueue.
    """
    implements(IPendingQueue)

    def __init__(self,
                 path=None,
                 dbfile=None,
                 isolation_level=None,
                 logger=None,
                ):

        self.path = path

        if path is None:
            dbfile = ':memory:'

        if dbfile is None:
            dbfile = os.path.join(path, 'pending.db')

        sql = self.sql = sqlite3.connect(dbfile,
                                         isolation_level=isolation_level)
        sql.text_factory = str

        found = sql.execute('select * from sqlite_master '
                             'where type = "table" and name = "pending"'
                           ).fetchall()
        if not found:
            sql.execute('create table pending'
                        '( id integer primary key'
                        ', message_id varchar(1024) unique'
                        ', quarantined boolean'
                        ', error_msg'
                        ')')

        if logger is not None and getattr(logger, 'log', None) is None:
            raise ValueError('logger must implement logging module interface.')

        self.logger = logger

    def push(self, message_id):
        """ See IPendingQueue.
        """
        self.sql.execute('insert into pending(message_id, quarantined) '
                         'values(?,?)', (message_id, False))

    def pop(self, how_many=1):
        """ See IPendingQueue.
        """
        cursor = self.sql.execute('select id, message_id from pending '
                                 'where quarantined=0 order by id')
        if how_many is None:
            rows = cursor.fetchall()
            how_many = len(rows)
        else:
            rows = cursor.fetchmany(how_many)
        cursor.close()
        count = 0
        popped_ids = []
        popped_m_ids = []
        while rows and count < how_many:
            id, m_id = rows.pop(0)
            popped_m_ids.append(m_id)
            popped_ids.append(str(id))
            count += 1
        if count < how_many:
            if self.logger is not None:
                self.logger.log('Queue underflow: requested %d, popped %d'
                                  % (how_many, count))
        set = ','.join(['"%s"' % x for x in popped_ids])
        self.sql.execute('delete from pending where id in (%s)' % set)
        return popped_m_ids

    def remove(self, message_id):
        """ See IPendingQueue.
        """
        cursor = self.sql.execute('delete from pending '
                                  'where message_id = "%s"' % message_id)
        if cursor.rowcount == 0:
            raise KeyError(message_id)

    def quarantine(self, message_id, error_msg=None):
        """ See IPendingQueue
        """
        if message_id in self:
            self.sql.execute(
                'update pending set quarantined=?, error_msg=? '
                'where message_id=?',
                (True, error_msg, message_id)
            )
        else:
            self.sql.execute(
                'insert into pending(message_id,quarantined,error_msg) '
                'values (?,?,?)',
                (message_id, True, error_msg)
            )

    def iter_quarantine(self):
        """ See IPendingQueue
        """
        results = self.sql.execute(
            'select message_id from pending where quarantined=1'
        )
        for result in results:
            yield result[0]

    def get_error_message(self, message_id):
        """ See IPendingQueue
        """
        error_msg = self.sql.execute(
            'select error_msg from pending '
            'where message_id=? and quarantined=1',
            (message_id,)
        ).fetchone()

        if error_msg is None:
            raise KeyError(message_id)
        return error_msg[0]

    def clear_quarantine(self):
        """ See IPendingQueue
        """
        self.sql.execute('update pending set quarantined=0, error_msg=null')

    def __nonzero__(self):
        """ See IPendingQueue.
        """
        return self.sql.execute(
            'select count(*) from pending where quarantined=0'
            ).fetchone()[0]

    def __iter__(self):
        return self.sql.execute(
            'select id, message_id from pending where quarantined=0'
        )

    def __contains__(self, message_id):
        cursor = self.sql.execute(
            'select message_id from pending where message_id=?', (message_id,)
            )
        contains = cursor.fetchone() is not None
        cursor.close()
        return contains

    def __del__(self):
        self.sql.close()
        del self.sql
