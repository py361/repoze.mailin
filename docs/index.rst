Documentation for repoze.mailin
###############################

:mod:`repoze.mailin` provides a framework for mapping inbound e-mail
onto application-defined handlers.

Table of Contents
=================

.. toctree::
   :maxdepth: 2

   api.rst

Message Store
=============

:mod:`repoze.mailin` defines an API, ``IMessageStore``, for plugins which
store :term:`RFC2822`-style messages.  Plugins can be configured dynamically
via an :term:`entry point`, which makes it possible to plug in a variety of
backing stores (e.g., `ZODB`, a relational database, or something like the
Goolge App Engine BigTable).

Within a store, messages are identified via a ``message_id``, derived
from the :term:`RFC2822` ``Message-Id`` header of the message.

.. note:  once stored, messages are read-only.


Message Format
--------------

:mod:`repoze.mailin` expects to process messages which are parseable
using Python's :mod:`email.parser` package, which creates a message object
consisting of the "headers" (as a mapping or sequence), plus the message
payload.


Attachments
-----------

:mod:`repoze.mailin` performs no special handling of attachments,
including nested :term:`RFC2822` messages, within a message.  Such attachments
can be extracted via the message object.


Integration with Mail Delivery
------------------------------

A given implementation of ``IMessageStore`` may be designed for easy
integration with a given type of mail delivery.  For instance, 
:class:`rezpoe.mailin.maildir.MaildirStore` is an implementation of
``IMessageStore``, based on the standard :class:`mailbox.Maildir`:  it
is designed to drain delivered messages from the "inbox" into a series
of date-stamped folders.

Other implementations might poll IMAP mailboxes, etc., or might plug
directly into the processing chain of a given :term:`MDA`.


Pending Queue
=============

As messages are ingested into the store, :mod:`repoze.mailin` records
their message IDs into a queue of pending messages.  The API for this
queue, ``IPendingQueue``, is implemented by a plugin defined via another
entry point.

Prerequisites
=============

This package requires Python 2.5 or later (Python 2.4's version of the
'mailbox' module and the 'email' package are not solid enough for this
application).

Plugins
=======

This package supplies the following plugin implementations:

    :class:`repoze.mailin.maildir.MaildirStore`
        implements ``IMessageStore`` using a standard :term:maildir,
        as implemented via the :module:`maildir` module in the Python
        standard library.  Ingested messages are stored in date-stamped
        folders within / under the main in-box;  the plugin provides
        an additional API for moving messages from the in-box into the
        appropriate sub-folder.  The plugin maintains an index of the
        ingested messages in a sqlite database table.

    :class:`repoze.mailin.pending.PendingQueue`
        implements ``IPendingQueue`` via a sqlite database table.

Glossary
========

.. glossary::

    entry point
        A conventional name, as defined by
        `setuptools <http://peak.telecommunity.com/DevCenter/setuptools>`_,
        which allows looking up a callable from an egg or a Python package.

    MDA
        "mail delivery agent", e.g., :command:`procmail` or
        :command:`maildrop`.

    RFC2822
        Standard e-mail / news message format, originally defined in
        `RFC 822 <http://www.faqs.org/rfcs/rfc822.html>`_,
        and later updated by
        `RFC 2822 <http://www.faqs.org/rfcs/rfc2822.html>`_.
