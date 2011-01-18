""" pollster [OPTIONS] maildir_path imap_host credentials

Poll the inbox of the IMAP account at 'imap_host', moving the messages
into date-based folders in a local maildir.

'maildir_path'
    the target maildir 

'imap_host'
    the hostname of the IMAP server, optionally contenated
    with the port number, e.g. 'imap.example.com' or 'imap.example.com:666'.

'credentials'
    either the account name / password (e.g., 'phred:secret') or a filename
    containing the same string.  The usual caveats apply for passing
    credentials on the command line, or in an unprotected file.

OPTIONS can include:

 --mailbox, -m          The name of the mailbox being polled: default, 'INBOX'.

 --ssl, -s              Use SSL (enabled by default if port is 993).

 --no-ssl, -S           Do not use SSL.

 --delete, -d           Delete messages after storing them locally (enabled
                        by default).

 --no-delete, -D        Do not delete messages after storing them locally.

 --pending-queue, -p    SQLite database filename for the 'pending queue'.
                        If omitted, no pending queue entries will be made.

 --limit, -l            Limit the number of messages polled.

 --dry-run, -n          Don't make any changes, just show what would be done.

 --verbose, -v          Be noisier (can be repeated).

 --quiet, -q            Don't emit any inessential output.

 --help, -h, -?         Print this message and exit.
"""
import email
import getopt
import imaplib
import os
import sys

from repoze.mailin.maildir import MaildirStore
from repoze.mailin.pending import PendingQueue

class IMAPError(Exception):
    def __init__(self, command, typ, data):
        self.command = command
        self.typ = typ
        self.data = data

    def __str__(self):
        return ('<IMAPError: command=%s, typ=%s, data=%s'
                 % (self.command, self.typ, self.data))

class Pollster:

    mailbox = 'INBOX'
    use_ssl = None
    delete = True
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
                                                   'm:sSdDp:l:nvqh?',
                                                   ['mailbox=',
                                                    'ssl',
                                                    'no-ssl',
                                                    'delete',
                                                    'no-delete',
                                                    'pending-queue=',
                                                    'limit=',
                                                    'dry-run',
                                                    'verbose',
                                                    'quiet',
                                                    'help',
                                                   ])
        except getopt.GetoptError, e:
            self.usage(str(e))

        for k, v in options:

            if k in ('-m', '--mailbox'):
                self.mailbox = v

            elif k in ('-s', '--ssl'):
                self.use_ssl = True

            elif k in ('-S', '--no-ssl'):
                self.use_ssl = False

            elif k in ('-d', '--delete'):
                self.delete = True

            elif k in ('-D', '--no-delete'):
                self.delete = False

            elif k in ('-p', '--pending-queue'):
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

        if len(arguments) != 3:
            self.usage('Arguments: maildir_path, imap_host, credentials')

        maildir_path, imap_host, credentials = arguments
        maildir_path = os.path.abspath(maildir_path)

        if not os.path.isdir(maildir_path):
            self.usage('Invalid maildir_path: %s' % maildir_path)

        self.maildir_path = maildir_path

        if ':' in imap_host:
            imap_host, port = imap_host.split(':')
            port = int(port)
        else:
            port = 143
        self.imap_host = imap_host
        self.imap_port = port

        if self.use_ssl is None:
            self.use_ssl = (port == 993)

        self.credentials = credentials
        if ':' not in credentials:
            credentials = open(credentials).readline()

        self.account, self.password = credentials.split(':')

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

    def connect_to_imap(self):
        if self.use_ssl:
            conn = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
        else:
            conn = imaplib.IMAP4(self.imap_host, self.imap_port)

        typ, data = conn.login(self.account, self.password)
        if typ != 'OK':
            raise IMAPError('login', typ, data)

        typ, data = conn.select(self.mailbox, readonly=self.dry_run)
        if typ != 'OK':
            raise IMAPError('select(%s)' % self.mailbox, typ, data)

        return conn

    def format_seqnums(self, seqnums):
        # Format a list of message sequence numbers into a form acceptable
        # to 'fetch' and other IMAP commands.
        if len(seqnums) == 1:
            return seqnums[0]
        ranges = []
        i = 0
        start = int(seqnums[0])
        for num in seqnums:
            num = int(num)
            try:
                next = seqnums[i+1]
            except IndexError:
                ranges.append((start, num))
                break
            if next > num + 1:
                ranges.append((start, num))
                start = next
            i = i + 1
        return ','.join(['%s:%s' % (start, end) for (start, end) in ranges])

    def fetch_next(self):
        conn = self.connect_to_imap()
        typ, data = conn.search(None, 'ALL')
        if typ != 'OK':
            raise IMAPError('search(ALL)', typ, data)
        seqnums = self.format_seqnums(data[0].split(' '))
        if seqnums:
            typ, data = conn.fetch(seqnums, '(RFC822)')
            if typ != 'OK':
                raise IMAPError('fetch', typ, data)
            drained = []
            count = 0
            for d in data:
                if type(d) is tuple: # message body
                    message = email.message_from_string(d[1])
                    message_id = message['Message-ID']
                    yield message_id, message
                    drained.append(d[0])
                    count += 1
                    if self.limit and count > self.limit:
                        break
            if self.delete and not self.dry_run:
                typ, data = conn.store(drained, '+FLAGS', '\\Deleted')
                if typ != 'OK':
                    raise IMAPError('store(Deleted)', typ, data)
                typ, data = conn.expunge()
                if typ != 'OK':
                    raise IMAPError('expunge', typ, data)

    def do_poll(self):
        if self.pending_queue is not None:
            pq = PendingQueue(self.pending_queue)
        else:
            pq = PendingQueue()

        md = MaildirStore(self.maildir_path)
        for message_id, message in self.fetch_next():
            if not self.dry_run:
                md[message_id] = message
                pq.push(message_id)
            if self.verbose > 1:
                print ' -', message_id

    def run(self):
        if self.verbose:
            print '=' * 78
            print 'IMAP server:port : ', '%s:%s' % (self.imap_host,
                                                    self.imap_port)
            print 'Account          : ', self.account
            print 'Target mailbox   : ', self.maildir_path
            print '=' * 78

            print 'Dry-run?         : ', self.dry_run
            print 'Mailbox          : ', self.mailbox
            print 'Use SSL?         : ', self.use_ssl
            print 'Delete?          : ', self.delete
            print 'Pending queue    : ', self.pending_queue

        self.do_poll()

        if self.verbose:
            print

def main(argv=None):
    if argv is None:
        argv = sys.argv
    Pollster(argv).run()

if __name__ == '__main__':
    main()
