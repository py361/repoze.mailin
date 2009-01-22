""" draino [OPTIONS] maildir_path

"Drain" the inbox of the maildir at 'maildir_path', moving the messages
into date-based folders.

OPTIONS can include:

 --pending-queue, -p    SQLite database filename for the 'pending queue'.
                        If omitted, no pending queue entries will be made.

 --limit, -l            Limit the number of messages drained.

 --dry-run, -n          Don't make any changes, just show what would be done.

 --verbose, -v          Be noisier (can be repeated).

 --quiet, -q            Don't emit any inessential output.

 --help, -h, -?         Print this message and exit.
"""
import getopt
import os
import sys

from repoze.mailin.maildir import MaildirStore
from repoze.mailin.pending import PendingQueue

class Draino:

    pending_queue = None
    limit = None
    dry_run = False
    verbose = 1

    def __init__(self, argv):
        self.parseOptions(argv)

    def parseOptions(self, argv):
        pending_queue = None
        try:
            options, arguments = getopt.gnu_getopt(argv[1:],
                                                   'p:l:nvqh?',
                                                   ['pending-queue=',
                                                    'limit=',
                                                    'dry-run',
                                                    'verbose',
                                                    'quiet',
                                                    'help',
                                                   ])
        except getopt.GetoptError, e:
            self.usage(str(e))

        for k, v in options:

            if k in ('-p', '--pending-queue'):
                pending_queue = v

            elif k in ('-l', '--limit'):
                try:
                    self.limit = int(v)
                except ValueError:
                    self.usage('Limit must be an integer: %s' % v)

            elif k in ('-n', '--dry-run'):
                self.dry_run = True

            elif k in ('-v', '--verbose'):
                self.verbose += 1

            elif k in ('-q', '--quiet'):
                self.verbose = 0

            elif k in ('-h', '-?', '--help'):
                self.usage(rc=2)

            else:
                self.usage('Unknown option: %s' % k)

        if len(arguments) != 1:
            self.usage('Must supply maildir_path')

        maildir_path, = arguments
        maildir_path = os.path.abspath(maildir_path)

        if not os.path.isdir(maildir_path):
            self.usage('Invalid maildir_path: %s' % maildir_path)

        self.maildir_path = maildir_path

        if pending_queue is not None:
            pending_queue = os.path.abspath(pending_queue)
            base, file = os.path.split(pending_queue)
            if not os.path.isdir(base):
                self.usage('Invalid directory for pending queue: %s'
                                % pending_queue)

        self.pending_queue = pending_queue

    def usage(self, message=None, rc=1):
        print __doc__
        if message is not None:
            print message
            print 
        sys.exit(rc)

    def do_drain(self):
        if self.pending_queue is not None:
            pq = PendingQueue(self.pending_queue)
        else:
            pq = PendingQueue()

        md = MaildirStore(self.maildir_path)
        for drained in md.drainInbox(pq, self.limit, self.dry_run):
            if self.verbose > 1:
                print ' -', drained

        if not self.dry_run:
            md.sql.commit()
            pq.sql.commit()

    def run(self):
        if self.verbose:
            print '=' * 78
            print 'Draining mailbox : ', self.maildir_path
            print '=' * 78

            print 'Dry-run          : ', self.dry_run
            print 'Pending queue    : ', self.pending_queue

        self.do_drain()

        if self.verbose:
            print

def main(argv=None):
    if argv is None:
        argv = sys.argv
    Draino(argv).run()

if __name__ == '__main__':
    main()
