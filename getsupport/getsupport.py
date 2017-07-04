#!/usr/bin/env python
# -*- coding: utf-8

# Copyright (C) 2015 – 2017 Natenom <natenom@googlemail.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:

# - Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
# - Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# - Neither the name of the Mumble Developers nor the names of its
#   contributors may be used to endorse or promote products derived from this
#   software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# `AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE FOUNDATION OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from mumo_module import (commaSeperatedIntegers,
                         commaSeperatedBool,
                         commaSeperatedStrings,
                         MumoModule)
import re
import string

class getsupport(MumoModule):
    default_config = {'getsupport':(
                                     ('servers', commaSeperatedIntegers, []),
                                   ),
                                lambda x: re.match('(all)|(server_\d+)', x):(
                                    ('supportgroup', str, 'supporter'),
                                    ('supportmessage_max_length', int, 160),
                                    ('cmds_create_request', commaSeperatedStrings, 'request, support, helpme'),
                                    ('cmds_list_requests', commaSeperatedStrings, 'requests, listrequests'),
                                    ('cmds_deleterequest', commaSeperatedStrings, 'deleterequest, removerequest'),
                                    ('controlcharacter', str, '!'),
                                    ('cmd_print_help', str, 'help'),
                                    ('msg_confirmation', str, 'The following request has been sent:<br />%s<br /><br />Please wait...<br />'),
                                    ('msg_nosupportmessage', str, "<span style='color:red;'>You need to add a request message in order to create a request :), try again...</span>"),
                                    ('msg_request_already_ongoing', str, 'here is already an ongoing request for you, please be patient and to not spam.'),
                                    ('msg_print_request_template', str, '<br /><span style="color:red;">Support request from %s:</span><br />Subject: %s</span>'),
                                    ('notify_about_unregistered_users', commaSeperatedBool, [True]),
                                    ('msg_print_unregisteredusernotification_template', str, '<br /><span style="color:red;">A new unregistered user named %s joined the server.<br />You got this messsage because you are a member of the supporter group.</span>')
                                )
                    }

    def __init__(self, name, manager, configuration = None):
        MumoModule.__init__(self, name, manager, configuration)
        self.murmur = manager.getMurmurModule()
        self.ongoingrequests = {}

    def isSupporter(self, userid, server):
        """ Check if a user is member of the supporter group in the root channel. """

        try:
            scfg = getattr(self.cfg(), 'server_%d' % server.id())
        except AttributeError:
            scfg = self.cfg().all

        ACL=server.getACL(0) #Get root acl.
        for group in ACL[1]:
            if (group.name == scfg.supportgroup):
                if userid in group.members:
                    return True
                else:
                    return False

    def connected(self):
        manager = self.manager()
        log = self.log()
        log.debug("Register for Server callbacks")

        servers = self.cfg().getsupport.servers
        if not servers:
            servers = manager.SERVERS_ALL

        manager.subscribeServerCallbacks(self, servers)

    def disconnected(self): pass

    #
    #--- Server callback functions
    #

    def getNameBySession(self, session, server):
        onlineUsers = server.getUsers() # We need this object to get the username for a session id.
        for currentuser in onlineUsers:
            if currentuser == session:
                return onlineUsers[session].name
                break

    def parseMessage(self, msg, server, user):
        """
            We get something like "!request bla blu bli" or "!requests" and want to get the following parts out of it:
            command = "request"
            arguments = "bla blu bli"

            or

            command = "requests"
            arguments = None

            If the message does not start with the controlcharacter both return values are None.
        """

        try:
            scfg = getattr(self.cfg(), 'server_%d' % server.id())
        except AttributeError:
            scfg = self.cfg().all

        log = self.log()

        if msg.startswith(scfg.controlcharacter) and len(msg) > len(scfg.controlcharacter):
            msg = msg.split(scfg.controlcharacter)[1] #remove controlcharacter from msg
            command = msg.split(" ")[0]
            arguments = msg[msg.find(command)+len(command)+1:]

            if arguments == "":
                arguments = None
            else:
                # Clean user message for security reasons (?) necessary?
                # http://stackoverflow.com/questions/3939361/remove-specific-characters-from-a-string-in-python
                allow = string.letters + string.digits + ' ,.'
                arguments=re.sub('[^%s]' % allow, '', arguments)

                if command in scfg.cmds_create_request: #Apply maximum length for support message.
                        if len(arguments) > scfg.supportmessage_max_length:
                            arguments = arguments[:scfg.supportmessage_max_length]

            log.debug("msg: %s, command: %s, arguments: %s, user.session: %s" % (msg, command, arguments, user.session))
        else:
            command = None
            arguments = None

        return command, arguments

    def userTextMessage(self, server, user, message, current=None):
        try:
            scfg = getattr(self.cfg(), 'server_%d' % server.id())
        except AttributeError:
            scfg = self.cfg().all

        log = self.log()

        command, messagefromuser = self.parseMessage(message.text, server, user)

        if command:
            if command == scfg.cmd_print_help:
                server.sendMessage(user.session, "Commands for the getsupport module:<br /><ul>" \
                    + "<li>"+scfg.controlcharacter+"<b>help</b></li>" \
                    + "<li>"+scfg.controlcharacter+"<b>requests</b></li>" \
                    + "<li>"+scfg.controlcharacter+"<b>deleterequest</b> &lt;ticket id&gt;</li>" \
                    + "<li>"+scfg.controlcharacter+"<b>request</b> followed by a short description</li>" \
                    + "</ul>")

            elif command in scfg.cmds_deleterequest:
                if self.isSupporter(user.userid, server):
                    try:
                        del self.ongoingrequests[int(messagefromuser)]
                        server.sendMessage(user.session, "Ticket ID %s successfully removed." % int(messagefromuser))
                    except:
                        log.debug("Tried to remove non existent ongoing request for session %s." % int(messagefromuser))

            elif command in scfg.cmds_list_requests:
                if self.isSupporter(user.userid, server):

                    table="<table border='1'><tr><td>Ticket ID</td><td>Username</td><td>Subject</td></tr>"

                    for session in self.ongoingrequests:
                        # Build a row per ongoing request.
                        # We have the session id and want the username...
                        table+="<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (session, self.getNameBySession(session, server), self.ongoingrequests[session])

                    table+="</table>"
                    server.sendMessage(user.session, table)

            elif command in scfg.cmds_create_request:
                if user.session in self.ongoingrequests:
                    server.sendMessage(user.session, scfg.msg_request_already_ongoing)
                    log.debug("%s requested new support while an ongoing request esists, ignoring this one." % user.name)
                else:
                    if messagefromuser:
                        self.ongoingrequests[user.session] = messagefromuser

                        #Send a confirmation to the user about the sent request.
                        server.sendMessage(user.session, scfg.msg_confirmation % messagefromuser)

                        ACL=server.getACL(0) #Get root acl to get list of supporters
                        for group in ACL[1]:
                            if (group.name == scfg.supportgroup):
                                supporter = group.members
                                break

                        onlineusers=server.getUsers()
                        for currentuser in onlineusers:
                            if onlineusers[currentuser].userid in supporter:
                                server.sendMessage(onlineusers[currentuser].session, scfg.msg_print_request_template % (user.name, messagefromuser))
                    else:
                        server.sendMessage(user.session, scfg.msg_nosupportmessage)

    def userConnected(self, server, user, context = None):
        try:
            scfg = getattr(self.cfg(), 'server_%d' % server.id())
        except AttributeError:
            scfg = self.cfg().all

        if scfg.notify_about_unregistered_users:
            if user.userid == -1:
                state = server.getState(user.session)
                if state.release.startswith("mumble-ruby"): #ignore mumble-ruby-pluginbots
                    return
                else:
                    ACL=server.getACL(0) #Get root acl to get list of supporters
                    for group in ACL[1]:
                        if (group.name == scfg.supportgroup):
                            supporter = group.members
                            break

                    onlineusers=server.getUsers()
                    for currentuser in onlineusers:
                        if onlineusers[currentuser].userid in supporter:
                            server.sendMessage(onlineusers[currentuser].session, scfg.msg_print_unregisteredusernotification_template % (user.name))

    def userDisconnected(self, server, state, context = None):
        if state.session in self.ongoingrequests:
            del self.ongoingrequests[state.session]

    def userStateChanged(self, server, state, context = None): pass
    def channelCreated(self, server, state, context = None): pass
    def channelRemoved(self, server, state, context = None): pass
    def channelStateChanged(self, server, state, context = None): pass
