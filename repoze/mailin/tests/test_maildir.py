import unittest

class MaildirStoreTests(unittest.TestCase):

    _tempdir = None

    def tearDown(self):
        if self._tempdir is not None:
            import shutil
            shutil.rmtree(self._tempdir)

    def _getTargetClass(self):
        from repoze.mailin.maildir import MaildirStore
        return MaildirStore

    def _makeOne(self, path=None, dbfile=':memory:'):
        if path is None:
            path = self._getTempdir()
        return self._getTargetClass()(path, dbfile)

    def _getTempdir(self):
        import tempfile
        if self._tempdir is None:
            self._tempdir = tempfile.mkdtemp()
        return self._tempdir

    def _makeMessageText(self, message_id='<abc123@example.com>', when=None):
        try:
            from email.utils import formatdate
        except ImportError: # Python 2.4
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
        import mailbox
        import os
        td = self._getTempdir()
        md_name = os.path.join(td, 'Maildir')
        md = mailbox.Maildir(md_name, factory=None, create=True)
        for message_id in message_ids:
            md.add(self._makeMessageText(message_id))

    def test_class_conforms_to_IMessageStore(self):
        from zope.interface.verify import verifyClass
        from repoze.mailin.interfaces import IMessageStore
        verifyClass(IMessageStore, self._getTargetClass())

    def test_instance_conforms_to_IMessageStore(self):
        from zope.interface.verify import verifyObject
        from repoze.mailin.interfaces import IMessageStore
        verifyObject(IMessageStore, self._makeOne())

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

        from sqlite3 import IntegrityError
        pq = DummyPQ()
        self.assertRaises(IntegrityError, list, md.drainInbox(pq))

        self.assertEqual(len(list(md.iterkeys())), 2)
        self.assertEqual(len(root), 1)
        self.assertEqual(pq._pushed, MESSAGE_IDS[:2])

class DummyPQ:
    def __init__(self):
        self._pushed = []

    def push(self, message_id):
        self._pushed.append(message_id)
