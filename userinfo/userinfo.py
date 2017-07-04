#!/usr/bin/env python
# -*- coding: utf-8

# Copyright (C) 2017 Natenom <natenom@googlemail.com>
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
                         commaSeperatedStrings,
                         commaSeperatedBool,
                         MumoModule)
import re
import Murmur
from hashlib import sha1

class userinfo(MumoModule):
    default_config = {'userinfo':(
                        ('servers', commaSeperatedIntegers, []),
                        ),
                        lambda x: re.match('(all)|(server_\d+)', x):(
                        ('canuseinfo', commaSeperatedStrings, ["admin", "hilfsadmin"]),
                        ('contextmenu_text', str, "Get some information about this user.")
                        )
                    }

    def __init__(self, name, manager, configuration = None):
        MumoModule.__init__(self, name, manager, configuration)
        self.murmur = manager.getMurmurModule()
        self.action_userinfo = manager.getUniqueAction()

    def connected(self):
        manager = self.manager()
        log = self.log()
        log.debug("Register for Server callbacks")

        servers = self.cfg().userinfo.servers
        if not servers:
            servers = manager.SERVERS_ALL

        manager.subscribeServerCallbacks(self, servers)

    def disconnected(self): pass

    #
    #--- Server callback functions
    #

    def __on_userinfo(self, server, action, user, target):
        try:
            scfg = getattr(self.cfg(), 'server_%d' % server.id())
        except AttributeError:
            scfg = self.cfg().all

        assert action == self.action_userinfo

        info = server.getState(target.session)
        info.comment = ""

        info2 = {}
        info2['ipv6'] = ""
        info2['ipv4'] = ""

        if info.address[0] == 32:
            info2['iptype'] = "ipv6"
            info2['ipv6'] = "not yet implemented" #'.'.join(str(i) for i in info.address[0:16])
        else:
            info2['iptype'] = "ipv4"
            info2['ipv4'] = '.'.join(str(i) for i in info.address[12:16])

        if target.userid>0:
            info2['registered'] = "yes"
        else:
            info2['registered'] = "no"

        try:
            userCert = server.getCertificateList(target.session)
            userHash = sha1(userCert[0]).hexdigest()
        except IndexError:
            userHash = "- (no certificate)"

        server.sendMessage(user.session, "<span style='color:red;'><br>\
                                          Name: {name}<br><br> \
                                          Registered: {registered} <br>\
                                          Session id: {sessionid} <br> \
                                          Client version: {version} ({release})<br> \
                                          Operating System: {os} ({osversion})<br> \
                                          Hash of certificate (sha1): {userHash}<br><br> \
                                          <u>Network</u><br> \
                                          ipv4: {ipv4} (<a href='https://www.heise.de/netze/tools/whois/?rm=whois_query&target_object={ipv4}'>check whois online</a>)<br> \
                                          ipv6: {ipv6} (<a href='https://www.heise.de/netze/tools/whois/?rm=whois_query&target_object={ipv4}'>check whois online</a>)<br> \
                                          address (raw): {address}<br><br> \
                                          tcponly: {tcponly}<br> \
                                          udpPing: {udpPing}<br> \
                                          tcpPing: {tcpPing}<br><br> \
                                          <u>Miscellaneous</u><br> \
                                          onlinesecs: {onlinesecs}<br> \
                                          bytespersec: {bytespersec}<br> \
                                          idlesecs: {idlesecs}<br><br> \
                                          </span>".format(name=info.name, version=info.version, release=info.release, os=info.os, osversion=info.osversion, address=str(info.address), tcponly=info.tcponly, idlesecs=info.idlesecs, udpPing=info.udpPing, tcpPing=info.tcpPing, onlinesecs=info.onlinesecs, bytespersec=info.bytespersec, ipv4=info2['ipv4'], registered=info2['registered'], sessionid=info.session, userHash=userHash, ipv6=info2['ipv6']))


        #if (target.userid > 0):
        #    server.sendMessage(user.session, scfg.msg_already_registered)
        #else:
        #    userCert = server.getCertificateList(target.session)
        #    userHash = sha1(userCert[0]).hexdigest()
        #    userInfomap = {Murmur.UserInfo.UserName: target.name, Murmur.UserInfo.UserHash: userHash}
        #    try:
        #        server.registerUser(userInfomap)
        #        server.sendMessage(user.session, scfg.msg_success)
        #        server.sendMessage(target.session, scfg.msg_success_target)
        #    except:
        #        server.sendMessage(user.session, scfg.msg_error)

    def userTextMessage(self, server, user, message, current=None): pass

    def userConnected(self, server, user, context = None):
        try:
            scfg = getattr(self.cfg(), 'server_%d' % server.id())
        except AttributeError:
            scfg = self.cfg().all

        log = self.log()
        manager = self.manager()
        bHasPermission = False

        # Check whether user has permission to use info module and add a context menu entry.
        ACL=server.getACL(0)
        for group in ACL[1]:
            if (group.name in scfg.canuseinfo):
                if (user.userid in group.members):
                    bHasPermission = True
                    # We can't break here as there can be definied multiple groups.

        if bHasPermission:
            self.log().info("Adding menu entries for user " + user.name)

            manager.addContextMenuEntry(
                    server, # Server of user
                    user, # User which should receive the new entry
                    self.action_userinfo, # Identifier for the action
                    scfg.contextmenu_text, # Text in the client
                    self.__on_userinfo, # Callback called when user uses the entry
                    self.murmur.ContextUser # We only want to show this entry on users
            )

    def userDisconnected(self, server, state, context = None): pass
    def userStateChanged(self, server, state, context = None): pass
    def channelCreated(self, server, state, context = None): pass
    def channelRemoved(self, server, state, context = None): pass
    def channelStateChanged(self, server, state, context = None): pass
