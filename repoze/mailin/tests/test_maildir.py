import unittest

_marker = object()

class _Base(object):
    _tempdir = None

    def tearDown(self):
        if self._tempdir is not None:
            import shutil
            shutil.rmtree(self._tempdir)

    def _getTempdir(self):
        import tempfile
        if self._tempdir is None:
            self._tempdir = tempfile.mkdtemp()
        return self._tempdir


class SaneFilenameMaildirTests(_Base, unittest.TestCase):

    def setUp(self):
        super(SaneFilenameMaildirTests, self).setUp()

    def tearDown(self):
        super(SaneFilenameMaildirTests, self).tearDown()

    def _getTargetClass(self):
        from repoze.mailin.maildir import SaneFilenameMaildir
        return SaneFilenameMaildir

    def _makeOne(self, dirname=None, factory=None, create=True):
        if dirname is None:
            dirname = self._getTempdir()
        return self._getTargetClass()(dirname, factory, create)

    def test_ctor(self):
        from mailbox import Maildir
        md = self._makeOne()
        self.failUnless(isinstance(md, Maildir))


class MaildirStoreTests(_Base, unittest.TestCase):

    def _getTargetClass(self):
        from repoze.mailin.maildir import MaildirStore
        return MaildirStore

    def _makeOne(self,
                 path=None,
                 dbfile=':memory:',
                 isolation_level=_marker,
                ):
        if path is None:
            path = self._getTempdir()
        if isolation_level is _marker:
            return self._getTargetClass()(path, dbfile)
        return self._getTargetClass()(path, dbfile, isolation_level)

    def _makeMessageText(self, message_id='<abc123@example.com>', when=None):
        try:
            from email.utils import formatdate
        except ImportError: # pragma: no cover
            # Python 2.4
            from email.Utils import formatdate
        lines = ['Date: %s' % formatdate(when),
                 'Message-Id: %s' % message_id,
                 'Content-Type: text/plain',
                 '',
                 'Body text here.'
                ]
        return '\r\n'.join(lines)

    def _makeMessage(self, message_id='<abc123@example.com>', when=None):
        from email import message_from_string
        return message_from_string(self._makeMessageText(message_id, when))

    def _populateInbox(self, message_ids):
        import os
        from repoze.mailin.maildir import SaneFilenameMaildir
        td = self._getTempdir()
        md_name = os.path.join(td, 'Maildir')
        md = SaneFilenameMaildir(md_name, factory=None, create=True)
        for message_id in message_ids:
            uniq = md.add(self._makeMessageText(message_id))

    def test_class_conforms_to_IMessageStore(self):
        from zope.interface.verify import verifyClass
        from repoze.mailin.interfaces import IMessageStore
        verifyClass(IMessageStore, self._getTargetClass())

    def test_instance_conforms_to_IMessageStore(self):
        from zope.interface.verify import verifyObject
        from repoze.mailin.interfaces import IMessageStore
        verifyObject(IMessageStore, self._makeOne())

    def test_ctor_defaults(self):
        md = self._makeOne()
        self.failUnless(md.sql.execute(
                             'select * from sqlite_master '
                             'where type = "table" and name = "messages"'
                             ).fetchall())
        self.assertEqual(md.sql.isolation_level, None)

    def test_ctor_w_dbfile(self):
        import os
        path = self._getTempdir()
        md = self._makeOne(path, dbfile=None)
        self.failUnless(os.path.exists(os.path.join(md.path, 'metadata.db')))

    def test_ctor_w_isolation_level(self):
        md = self._makeOne(isolation_level='DEFERRED')
        self.assertEqual(md.sql.isolation_level, 'DEFERRED')

    def test_iterkeys_empty(self):
        md = self._makeOne()
        self.assertEqual(len(list(md.iterkeys())), 0)

    def test_iterkeys_inbox_not_empty(self):
        MESSAGE_IDS = ['<abcdef@example.com>',
                       '<defghi@example.com>',
                       '<ghijkl@example.com>',
                      ]
        self._populateInbox(MESSAGE_IDS)
        md = self._makeOne()
        self.assertEqual(len(list(md.iterkeys())), 0)

    def test___getitem___nonesuch(self):
        md = self._makeOne()
        self.assertRaises(KeyError, lambda: md['nonesuch'])

    def test___getitem___valid_message_id_no_datestamp_folder(self):
        import os
        import mailbox
        path = self._getTempdir()
        root = mailbox.Maildir(os.path.join(path, 'Maildir'),
                               factory=None, create=True)
        md = self._makeOne(path)
        md.sql.execute('insert into messages'
                        '(message_id, year, month, day, maildir_key)'
                       ' values("ABC", 2009, 6, 23, "ABC")')
        self.assertRaises(KeyError, lambda: md['ABC'])

    def test___getitem___valid_message_id_w_datestamp_folder_wo_message(self):
        import os
        import mailbox
        path = self._getTempdir()
        root = mailbox.Maildir(os.path.join(path, 'Maildir'),
                               factory=None, create=True)
        root.add_folder('2009.06.23')
        md = self._makeOne(path)
        md.sql.execute('insert into messages'
                         '(message_id, year, month, day, maildir_key)'
                       ' values("ABC", 2009, 6, 23, "ABC")')
        self.assertRaises(KeyError, lambda: md['ABC'])

    def test___getitem___valid_message_id_w_datestamp_folder_w_message(self):
        import os
        import mailbox
        path = self._getTempdir()
        root = mailbox.Maildir(os.path.join(path, 'Maildir'),
                               factory=None, create=True)
        root.add_folder('2009.06.23')
        folder = root.get_folder('2009.06.23')
        to_store = mailbox.MaildirMessage('STORE_ME')
        key = folder.add(to_store)
        md = self._makeOne(path)
        md.sql.execute('insert into messages'
                         '(message_id, year, month, day, maildir_key)'
                       ' values("ABC", 2009, 6, 23, "%s")' % key)
        message = md['ABC'] # doesn't raise

    def test___setitem___text(self):
        import calendar
        import time
        MESSAGE_ID ='<defghi@example.com>'
        WHEN = time.strptime('2008-10-03T14:00:00-GMT',
                             '%Y-%m-%dT%H:%M:%S-%Z')
        md = self._makeOne()
        text = self._makeMessageText(message_id=MESSAGE_ID,
                                     when=calendar.timegm(WHEN))
        md[MESSAGE_ID] = text
        found = md[MESSAGE_ID]
        self.assertEqual(found['Date'],
                         time.strftime('%a, %d %b %Y %H:%M:%S -0000', WHEN))
        self.assertEqual(found['Message-Id'], MESSAGE_ID)
        self.failUnless(MESSAGE_ID in list(md.iterkeys()))

        folder = md._getMaildir('2008.10.03', create=False)
        keys = list(folder.iterkeys())
        self.assertEqual(len(keys), 1)


    def test___setitem___message_object(self):
        MESSAGE_ID ='<defghi@example.com>'
        md = self._makeOne()
        message = self._makeMessage(message_id=MESSAGE_ID)
        md[MESSAGE_ID] = message
        found = md[MESSAGE_ID]
        self.assertEqual(found['Date'], message['Date'])
        self.assertEqual(found['Message-Id'], message['Message-Id'])
        self.failUnless(MESSAGE_ID in list(md.iterkeys()))

    def test_drainInbox_empty_wo_pq(self):
        md = self._makeOne()
        root = md._getMaildir()

        self.assertEqual(len(list(md.iterkeys())), 0)
        self.assertEqual(len(root), 0)

        drained = list(md.drainInbox())

        self.assertEqual(len(drained), 0)
        self.assertEqual(len(list(md.iterkeys())), 0)
        self.assertEqual(len(root), 0)

    def test_drainInbox_empty_w_pq(self):
        md = self._makeOne()
        root = md._getMaildir()

        pq = DummyPQ()
        self.assertEqual(pq._pushed, [])

        drained = list(md.drainInbox(pq))

        self.assertEqual(len(drained), 0)
        self.assertEqual(pq._pushed, [])

    def test_drainInbox_not_empty_wo_pq(self):
        MESSAGE_IDS = ['<abcdef@example.com>',
                       '<defghi@example.com>',
                       '<ghijkl@example.com>',
                      ]
        self._populateInbox(MESSAGE_IDS)

        md = self._makeOne()
        root = md._getMaildir()
        self.assertEqual(len(list(md.iterkeys())), 0)
        self.assertEqual(len(root), len(MESSAGE_IDS))

        drained = list(md.drainInbox())

        self.assertEqual(drained, MESSAGE_IDS)
        self.assertEqual(len(list(md.iterkeys())), len(MESSAGE_IDS))
        self.assertEqual(len(root), 0)

    def test_drainInbox_not_empty_wo_pq_dry_run(self):
        MESSAGE_IDS = ['<abcdef@example.com>',
                       '<defghi@example.com>',
                       '<ghijkl@example.com>',
                      ]
        self._populateInbox(MESSAGE_IDS)

        md = self._makeOne()
        root = md._getMaildir()
        self.assertEqual(len(list(md.iterkeys())), 0)
        self.assertEqual(len(root), len(MESSAGE_IDS))

        drained = list(md.drainInbox(dry_run=True))

        self.assertEqual(drained, MESSAGE_IDS)
        self.assertEqual(len(list(md.iterkeys())), 0)
        self.assertEqual(len(root), len(MESSAGE_IDS))

    def test_drainInbox_not_empty_w_pq(self):
        MESSAGE_IDS = ['<abcdef@example.com>',
                       '<defghi@example.com>',
                       '<ghijkl@example.com>',
                      ]
        self._populateInbox(MESSAGE_IDS)

        md = self._makeOne()
        root = md._getMaildir()

        pq = DummyPQ()
        list(md.drainInbox(pq)) # consume generator

        self.assertEqual(pq._pushed, MESSAGE_IDS)

    def test_drainInbox_not_empty_w_pq_w_limit(self):
        MESSAGE_IDS = ['<abcdef@example.com>',
                       '<defghi@example.com>',
                       '<ghijkl@example.com>',
                      ]
        self._populateInbox(MESSAGE_IDS)

        md = self._makeOne()
        root = md._getMaildir()

        pq = DummyPQ()
        drained = list(md.drainInbox(pq, limit=2))

        self.assertEqual(drained, MESSAGE_IDS[:2])
        self.assertEqual(len(list(md.iterkeys())), 2)
        self.assertEqual(len(root), 1)
        self.assertEqual(pq._pushed, MESSAGE_IDS[:2])

    def test_drainInbox_not_empty_w_pq_dup_ids(self):
        MESSAGE_IDS = ['<abcdef@example.com>',
                       '<defghi@example.com>',
                       '<defghi@example.com>',
                      ]
        self._populateInbox(MESSAGE_IDS)

        md = self._makeOne()
        root = md._getMaildir()

        pq = DummyPQ()
        drained = list(md.drainInbox(pq))

        self.assertEqual(drained, MESSAGE_IDS[:2])
        self.assertEqual(len(list(md.iterkeys())), 2)
        self.assertEqual(len(root), 0)
        self.assertEqual(pq._pushed, MESSAGE_IDS[:2])


class DummyPQ:
    def __init__(self):
        self._pushed = []

    def push(self, message_id):
        self._pushed.append(message_id)
