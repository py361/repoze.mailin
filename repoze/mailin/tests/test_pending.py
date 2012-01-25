import unittest

_marker = object()

class PendingQueueTests(unittest.TestCase):

    _tempdir = None

    def tearDown(self):
        if self._tempdir is not None:
            import shutil
            shutil.rmtree(self._tempdir)

    def _getTargetClass(self):
        from repoze.mailin.pending import PendingQueue
        return PendingQueue

    def _makeOne(self,
                 path=None,
                 dbfile=':memory:',
                 isolation_level=_marker,
                 logger=_marker,
                ):
        if logger is _marker:
            if isolation_level is _marker:
                return self._getTargetClass()(path, dbfile)
            return self._getTargetClass()(path, dbfile, isolation_level)

        if isolation_level is _marker:
            return self._getTargetClass()(path, dbfile, logger=logger)

        return self._getTargetClass()(path, dbfile, isolation_level, logger)

    def test_class_conforms_to_IPendingQueue(self):
        from zope.interface.verify import verifyClass
        from repoze.mailin.interfaces import IPendingQueue
        verifyClass(IPendingQueue, self._getTargetClass())

    def test_instance_conforms_to_IPendingQueue(self):
        from zope.interface.verify import verifyObject
        from repoze.mailin.interfaces import IPendingQueue
        verifyObject(IPendingQueue, self._makeOne())

    def test_ctor_defaults(self):
        pq = self._getTargetClass()()
        self.assertEqual(pq.path, None)
        self.assertEqual(pq.sql.isolation_level, None) # autocommit
        self.assertEqual(pq.logger, None)

    def test_ctor_w_path_wo_dbfile(self):
        import os
        import tempfile
        tempdir = self._tempdir = tempfile.mkdtemp()
        pq = self._makeOne(tempdir, None)
        self.assertEqual(pq.path, tempdir)
        self.failUnless(os.path.isfile(os.path.join(tempdir, 'pending.db')))

    def test_ctor_w_isolation_level(self):
        pq = self._makeOne(isolation_level='DEFERRED')
        self.assertEqual(pq.sql.isolation_level, 'DEFERRED')

    def test_ctor_w_invalid_logger(self):
        logger = object()
        self.assertRaises(ValueError, self._makeOne, logger=logger)

    def test_ctor_w_logger(self):
        logger = DummyLogger()
        pq = self._makeOne(logger=logger)
        self.failUnless(pq.logger is logger)

    def test_ctor_w_isolation_level_and_logger(self):
        logger = DummyLogger()
        pq = self._makeOne(isolation_level='DEFERRED', logger=logger)
        self.assertEqual(pq.sql.isolation_level, 'DEFERRED')
        self.failUnless(pq.logger is logger)

    def test___nonzero___empty(self):
        pq = self._makeOne()
        self.failIf(pq)

    def test___iter___empty(self):
        pq = self._makeOne()
        self.failIf(list(pq))

    def test_pop_empty_returns_empty(self):
        pq = self._makeOne()
        self.assertEqual(list(pq.pop()), [])

    def test_pop_empty_w_logger(self):
        logger = DummyLogger()
        pq = self._makeOne(logger=logger)
        pq.pop()
        self.assertEqual(len(logger._logged), 1)
        self.assertEqual(logger._logged[0],
                         (('Queue underflow: requested 1, popped 0',), {}))

    def test_pop_empty_with_many(self):
        logger = DummyLogger()
        pq = self._makeOne(logger=logger)
        found = pq.pop(2)
        self.assertEqual(len(found), 0)
        self.assertEqual(logger._logged[0],
                         (('Queue underflow: requested 2, popped 0',), {}))

    def test_pop_empty_with_None(self):
        logger = DummyLogger()
        pq = self._makeOne(logger=logger)
        found = pq.pop(None)
        self.assertEqual(len(found), 0)
        self.failIf(logger._logged)

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
        pq.pop()
        self.failIf(pq)

    def test_pop_nonempty_with_None(self):
        MESSAGE_ID_1 ='<defghi@example.com>'
        MESSAGE_ID_2 ='<jklmn@example.com>'
        pq = self._makeOne()
        pq.push(MESSAGE_ID_1)
        pq.push(MESSAGE_ID_2)
        popped = pq.pop(None)
        self.failIf(pq)
        self.assertEqual(popped, [MESSAGE_ID_1, MESSAGE_ID_2])

    def test_push_then_pop_returns_message_ID(self):
        MESSAGE_ID ='<defghi@example.com>'
        pq = self._makeOne()
        pq.push(MESSAGE_ID)
        found = pq.pop()
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0], MESSAGE_ID)

    def test_push_then_remove(self):
        MESSAGE_ID ='<defghi@example.com>'
        pq = self._makeOne()
        pq.push(MESSAGE_ID)
        pq.remove(MESSAGE_ID)
        self.failIf(pq)

    def test_pop_not_empty_with_many(self):
        MESSAGE_IDS = ['<abcdef@example.com>',
                       '<defghi@example.com>',
                       '<ghijkl@example.com>',
                      ]
        pq = self._makeOne()
        for message_id in MESSAGE_IDS:
            pq.push(message_id)
        found = pq.pop(2)
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
        logger = DummyLogger()
        pq = self._makeOne(logger=logger)
        for message_id in MESSAGE_IDS:
            pq.push(message_id)
        found = pq.pop(5)
        self.assertEqual(len(found), 3)
        self.assertEqual(found[0], MESSAGE_IDS[0])
        self.assertEqual(found[1], MESSAGE_IDS[1])
        self.assertEqual(found[2], MESSAGE_IDS[2])
        residue = list(pq)
        self.assertEqual(len(residue), 0)
        self.assertEqual(logger._logged[0],
                         (('Queue underflow: requested 5, popped 3',), {}))

    def test_pop_nonunicode_message_id(self):
        # Message-Id is actual message id encountered in field,
        # which caused mail-in to break.
        MESSAGE_ID = '<086801c9f304$8a00d960$d958485f@\xef\xe0\xf8\xe0>'
        pq = self._makeOne()
        pq.push(MESSAGE_ID)
        found = pq.pop()
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0], MESSAGE_ID)
        residue = list(pq)
        self.assertEqual(len(residue), 0)

    def test_close_on_evict(self):
        pq = self._makeOne()
        sql = pq.sql = DummySql()
        pq = None
        self.failUnless(sql.closed)

    def test_quarantine_nonexisting_message_id(self):
        MESSAGE_ID = '<abcdef@example.com>'
        pq = self._makeOne()
        pq.quarantine(MESSAGE_ID)
        found = list(pq.iter_quarantine())
        self.assertEqual(len(found), 1)
        self.assertEqual(MESSAGE_ID, found[0])

    def test_quarantine_existing_message_id(self):
        MESSAGE_ID = '<abcdef@example.com>'
        pq = self._makeOne()
        pq.push(MESSAGE_ID)
        pq.quarantine(MESSAGE_ID)
        found = list(pq.iter_quarantine())
        self.assertEqual(len(found), 1)
        self.assertEqual(MESSAGE_ID, found[0])

    def test_dont_iterate_quarantined_message_id(self):
        MESSAGE_IDS = ['<abcdef@example.com>',
                       '<defghi@example.com>',
                       '<ghijkl@example.com>',
                      ]
        pq = self._makeOne()
        for message_id in MESSAGE_IDS:
            pq.push(message_id)
        pq.quarantine(MESSAGE_IDS[1])
        found = list(pq)
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0][1], '<abcdef@example.com>')
        self.assertEqual(found[1][1], '<ghijkl@example.com>')

    def test_dont_pop_quarantined_message_id(self):
        MESSAGE_IDS = ['<abcdef@example.com>',
                       '<defghi@example.com>',
                       '<ghijkl@example.com>',
                      ]
        pq = self._makeOne()
        for message_id in MESSAGE_IDS:
            pq.push(message_id)
        pq.quarantine(MESSAGE_IDS[1])
        found = list(pq.pop(3))
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0], '<abcdef@example.com>')
        self.assertEqual(found[1], '<ghijkl@example.com>')

    def test_clear_quarantine(self):
        MESSAGE_IDS = ['<abcdef@example.com>',
                       '<defghi@example.com>',
                       '<ghijkl@example.com>',
                      ]
        pq = self._makeOne()
        for message_id in MESSAGE_IDS:
            pq.push(message_id)
        pq.quarantine(MESSAGE_IDS[1])
        found = list(pq.pop(3))
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0], '<abcdef@example.com>')
        self.assertEqual(found[1], '<ghijkl@example.com>')

        pq.clear_quarantine()
        found = list(pq.pop(3))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0], '<defghi@example.com>')

    def test_quarantine_w_error_msg(self):
        MESSAGE_ID = '<abcdef@example.com>'
        pq = self._makeOne()
        pq.push(MESSAGE_ID)
        pq.quarantine(MESSAGE_ID, 'Error message')
        found = list(pq.iter_quarantine())
        self.assertEqual(len(found), 1)
        self.assertEqual(MESSAGE_ID, found[0])
        self.assertEqual('Error message', pq.get_error_message(MESSAGE_ID))

    def test_clear_quarantine_w_error_message(self):
        MESSAGE_IDS = ['<abcdef@example.com>',
                       '<defghi@example.com>',
                       '<ghijkl@example.com>',
                      ]
        pq = self._makeOne()
        for message_id in MESSAGE_IDS:
            pq.push(message_id)
        pq.quarantine(MESSAGE_IDS[1], 'Error message')
        found = list(pq.pop(3))
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0], '<abcdef@example.com>')
        self.assertEqual(found[1], '<ghijkl@example.com>')
        self.assertEqual(pq.get_error_message(MESSAGE_IDS[1]), 'Error message')

        pq.clear_quarantine()
        found = list(pq.pop(3))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0], '<defghi@example.com>')
        self.assertRaises(KeyError, pq.get_error_message, MESSAGE_IDS[1])

    def test_nonzero_with_quarantine(self):
        MESSAGE_IDS = ['<abcdef@example.com>',
                       '<defghi@example.com>',
                       '<ghijkl@example.com>',
                      ]
        pq = self._makeOne()
        for message_id in MESSAGE_IDS:
            pq.push(message_id)
        pq.quarantine(MESSAGE_IDS[1])
        found = []
        while pq:
            found.append(list(pq.pop())[0])
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0], '<abcdef@example.com>')
        self.assertEqual(found[1], '<ghijkl@example.com>')

class DummySql(object):
    closed = False

    def close(self):
        self.closed = True

class DummyLogger:
    def __init__(self):
        self._logged = []

    def log(self, *args, **kw):
        self._logged.append((args, kw))
