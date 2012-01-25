from zope.interface import Interface

class IMessageStore(Interface):
    """  Plugin interface for append-only storage of RFC822 messages.
    """
    def __getitem__(message_id):
        """ Retrieve a message.

        - Return an instance of 'email.Message'. (XXX text?)

        - Raise KeyError if no message with the given ID is found.
        """

    def __setitem__(message_id, message):
        """ Store a message.

        - 'message' should be an instance of 'email.Message'. (XXX text?)

        - Raise KeyError if no message with the given ID is found.
        """

    def iterkeys():
        """ Return an interator over the message IDs in the store.
        """

class IPendingQueue(Interface):
    """ Plugin interface for a FIFO queue of messages awaiting processing.
    """
    def push(message_id):
        """ Append 'message_id' to the queue.
        """

    def pop(how_many=1):
        """ Retrieve the next 'how_many' message IDs to be processed.

        - If 'how_many' is None, then return all available message IDs.

        - May return fewer than 'how_many' IDs, if the queue is emptied.

        - Popped messages are no longer present in the queue.
        """

    def remove(message_id):
        """ Remove the given message ID from the queue.

        - Raise KeyError if not found.
        """

    def quarantine(message_id, error_msg=None):
        """ Adds 'message_id' to quarantine for this queue.  Message must be
        moved out of quarantine before it can be processed.  May optionally
        pass in error_msg string as reason for the quarantine.

        """

    def iter_quarantine():
        """ Returns an iterator for message_ids that are in the quaratine.
        """

    def get_error_message(message_id):
        """ Returns the error message for the quarantined message_id.
        """

    def clear_quarantine():
        """ Moves all messages out of quarantine to retry processing.
        """

    def __nonzero__():
        """ Return True if no message IDs are in the queue, else False.
        """

class StopProcessing(Exception):
    """ Raised by IMessageFilter instances to halt procesing of a message.

    o The application may still commit the current transaction.
    """

class CancelProcessing(StopProcessing):
    """ Raised by IMessageFilter instances to halt procesing of a message.

    o The application must abort the current transaction.
    """

class IBlackboardFactory(Interface):
    """ Utility for creating a pre-initialized blackboard.
    """
    def __call__(message):
        """ Return an IBlackboard instance for the message.
        """

class IBlackboard(Interface):
    """ Mapping for recording the results of message processing.

    - API is that of a Python dict.
    """

class IMessageFilter(Interface):
    """ Plugin interface for processing messages.
    """
    def __call__(message, blackboard):
        """ Process / extract information from mesage and add to blackboard.

        - 'message' will be an instance of 'email.Message'.

        - 'blackboard' will be an 'IBlackboard.

        - Raise 'StopProcessing' to cancel further processing of 'message'.
        """
