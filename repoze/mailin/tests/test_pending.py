import unittest

class PendingQueueTests(unittest.TestCase):

    _tempdir = None

    def tearDown(self):
        if self._tempdir is not None:
            import shutil
            shutil.rmtree(self._tempdir)

    def _getTargetClass(self):
        from repoze.mailin.pending import PendingQueue
        return PendingQueue

    def _makeOne(self, path=None, dbfile=':memory:'):
        return self._getTargetClass()(path, dbfile)

    def test_class_conforms_to_IPendingQueue(self):
        from zope.interface.verify import verifyClass
        from repoze.mailin.interfaces import IPendingQueue
        verifyClass(IPendingQueue, self._getTargetClass())

    def test_instance_conforms_to_IPendingQueue(self):
        from zope.interface.verify import verifyObject
        from repoze.mailin.interfaces import IPendingQueue
        verifyObject(IPendingQueue, self._makeOne())

    def test_ctor_defaults(self):
        defaulted = self._getTargetClass()()
        self.assertEqual(defaulted.path, None)
        self.assertEqual(defaulted.sql.isolation_level, None) # autocommit

    def test___nonzero___empty(self):
        pq = self._makeOne()
        self.failIf(pq)

    def test_pop_empty_returns_None(self):
        pq = self._makeOne()
        self.assertEqual(list(pq.pop()), [])

    def test_remove_nonesuch_raises_KeyError(self):
        pq = self._makeOne()
        self.assertRaises(KeyError, pq.remove, 'nonesuch')

    def test_push_sets_nonzero(self):
        MESSAGE_ID ='<defghi@example.com>'
        pq = self._makeOne()
        pq.push(MESSAGE_ID)
        self.failUnless(pq)

    def test_pop_sets_nonzero(self):
        MESSAGE_ID ='<defghi@example.com>'
        pq = self._makeOne()
        pq.push(MESSAGE_ID)
        list(pq.pop())        # consume generator, ignore results
        self.failIf(pq)

    def test_push_then_pop_returns_message_ID(self):
        MESSAGE_ID ='<defghi@example.com>'
        pq = self._makeOne()
        pq.push(MESSAGE_ID)
        found = list(pq.pop())
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0], MESSAGE_ID)

    def test_push_then_remove(self):
        MESSAGE_ID ='<defghi@example.com>'
        pq = self._makeOne()
        pq.push(MESSAGE_ID)
        pq.remove(MESSAGE_ID)
        self.failIf(pq)

    def test_pop_not_empty_with_many(self):
        pq = self._makeOne()
        found = list(pq.pop(2))
        self.assertEqual(len(found), 0)

    def test_pop_not_empty_with_many(self):
        MESSAGE_IDS = ['<abcdef@example.com>',
                       '<defghi@example.com>',
                       '<ghijkl@example.com>',
                      ]
        pq = self._makeOne()
        for message_id in MESSAGE_IDS:
            pq.push(message_id)
        found = list(pq.pop(w))

    def test_pop_not_empty_with_many(self):
        MESSAGE_IDS = ['<abcdef@example.com>',
                       '<defghi@example.com>',
                       '<ghijkl@example.com>',
                      ]
        pq = self._makeOne()
        for message_id in MESSAGE_IDS:
            pq.push(message_id)
        found = list(pq.pop(2))
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0], MESSAGE_IDS[0])
        self.assertEqual(found[1], MESSAGE_IDS[1])
        residue = list(pq)
        self.assertEqual(len(residue), 1)

    def test_pop_not_empty_with_less_than_requested(self):
        MESSAGE_IDS = ['<abcdef@example.com>',
                       '<defghi@example.com>',
                       '<ghijkl@example.com>',
                      ]
        pq = self._makeOne()
        for message_id in MESSAGE_IDS:
            pq.push(message_id)
        found = list(pq.pop(5))
        self.assertEqual(len(found), 3)
        self.assertEqual(found[0], MESSAGE_IDS[0])
        self.assertEqual(found[1], MESSAGE_IDS[1])
        self.assertEqual(found[2], MESSAGE_IDS[2])
        residue = list(pq)
        self.assertEqual(len(residue), 0)

    def test_close_on_evict(self):
        pq = self._makeOne()
        sql = pq.sql = DummySql()
        pq = None
        self.failUnless(sql.closed)

class DummySql(object):
    closed = False

    def close(self):
        self.closed = True

