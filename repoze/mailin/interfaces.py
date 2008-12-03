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

        - May return fewer than 'how_many' IDs, if the queue is emptied.

        - Popped messages are no longer present in the queue.
        """

    def remove(message_id):
        """ Remove the given message ID from the queue.

        - Raise KeyError if not found.
        """

    def __nonzero__():
        """ Return True if no message IDs are in the queue, else False.
        """

class StopProcessing(Exception):
    """ Raised by IMessageFilter instances to halt procesing of a message.
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
