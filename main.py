#!/usr/bin/python
# -*- coding: utf-8 -*-

# These are only needed for Python v2 but are harmless for Python v3
import sip
sip.setapi('QString', 2)
sip.setapi('QVariant', 2)

import logging
import datetime
import sys
import re
from PyQt4.QtGui import *
from PyQt4.QtCore import SIGNAL, SLOT, QSettings, Qt
from PyQt4 import uic

import interface.resource.res
from BuddyList import BuddyList
from im import Client
from constants import SHOW, MUC_GROUP_TITLE, PATH_UI_MAIN, PATH_UI_CONNECTION, PATH_UI_LOGS, PATH_UI_ABOUT_PYTALK, PATH_UI_JOIN_MUC


class MainWindow(QMainWindow):	
	def __init__(self, parent=None):
		#QMainWindow.__init__(self, None, Qt.WindowStaysOnTopHint) # always on top
		super(MainWindow, self).__init__(parent)
		
		self.settings = QSettings("Dae-ekleN", "PyTalk")
		
		# add logs widget		
		QWidget.__init__(self)
		self.logsWidget = uic.loadUi(PATH_UI_LOGS)
		self.logsWidget.etx_logs.setReadOnly(True)
		
		# loading .ui
		uic.loadUi(PATH_UI_MAIN, self)
		
		# Set status Offline
		self.cmb_status_box.setCurrentIndex(5)
		self.cmb_status_box.setEnabled(False)
		self.eln_status_edit.hide()
		
		# connecting signals
		self.connect(self.cmb_status_box, SIGNAL("activated(int)"), self.statusUpdate)
		self.connect(self.eln_status_edit, SIGNAL("returnPressed()"), self.statusUpdate)
        
        # Set BuddyList
		self.BuddyList = BuddyList(self)
		self.vboxlayout.insertWidget(0, self.BuddyList)
		#self.connect(self.BuddyList, SIGNAL("rename"), self.addBuddy)
		
		# sleekxmpp connection
		self.im = None
		
		# Account
		self.act_connection.triggered.connect(self.showConnectDialog)
		self.connect(self.act_deconnection, SIGNAL("triggered()"), self.disconnect)
		self.connect(self.act_join_group_chat, SIGNAL("triggered()"), self.showMUCDialog)
		self.connect(self.act_quit, SIGNAL("triggered()"), self.quitApp)
		self.act_join_group_chat.setEnabled(False)
		self.act_add_a_buddy.setEnabled(False)
		
		# View
		self.act_away_buddies.setEnabled(False)
		self.act_offline_buddies.setEnabled(False)
		self.connect(self.act_away_buddies, SIGNAL("toogled()"), self.showAwayBuddies)
		self.connect(self.act_offline_buddies, SIGNAL("toogled()"), self.showOfflineBuddies)
		self.connect(self.act_away_buddies, SIGNAL("triggered()"), self.showAwayBuddies)
		self.connect(self.act_offline_buddies, SIGNAL("triggered()"), self.showOfflineBuddies)
		
		# Tools
		self.connect(self.act_logs, SIGNAL("triggered()"), self.showLogs)
		
		# About Dialogs
		self.connect(self.act_about_pytalk, SIGNAL("triggered()"), self.aboutPyTalk)
		self.connect(self.act_about_qt, SIGNAL("triggered()"), QApplication.instance(), SLOT("aboutQt()"))
		
	def aboutPyTalk(self):
		QDialog.__init__(self)
		self.aboutPyTalk = uic.loadUi(PATH_UI_ABOUT_PYTALK)
		self.aboutPyTalk.show()
		self.aboutPyTalk.raise_()
		
	def showMUCDialog(self):
		QDialog.__init__(self)
		self.joinGroupChat = uic.loadUi(PATH_UI_JOIN_MUC)
		self.joinGroupChat.show()
		self.connect(self.joinGroupChat, SIGNAL("accepted()"), self.joinMUC)
		
	def joinMUC(self):
		room = str(self.joinGroupChat.eln_room.text()) # dae-eklen-test2|dae-eklen-test|dae-eklen
		server = str(self.joinGroupChat.cmb_server.currentText())
		
		self.checkAndJoinMUC(room)

	def inviteMUC(self, room, jidFrom):
		if jidFrom:
			text = "Received invitation from " + jidFrom + " to room " + room
		else:
			text = "Received invitation to room " + room		
		text += "\n\nDo you want to accept the invitation?"
		
		reply = QMessageBox.question(self, "Groupchat invitation", text, QMessageBox.Yes, QMessageBox.No)
		if reply == QMessageBox.Yes:
			mucTitlePattern = """([\w\-][\w\-\.\|]*)+@[\w\-][\w\-\.]+[a-zA-Z]{1,4}"""
			name = re.findall(mucTitlePattern, room)
			self.checkAndJoinMUC(name[0])
		else:
			self.im.declineMUCInvite(room, jidFrom)
	
	def checkAndJoinMUC(self, roomName):
		jids = roomName.split("|")
		match = 0 
		users = []
		for el in range(len(jids)): 
			users.append(unicode(jids[el] + "@talkr.im"))
			if self.im.dicsoveryJid(users[el]): # if user exists
				match += 1
					
		if len(jids) == match and match != 0:
			# our type of group
			if not self.BuddyList.MUCExists(users):
				self.im.joinMUC(users)
			else:
				self.information("Join Group Chat", "Specified room is already added to '" + MUC_GROUP_TITLE + "' group.")
		else:
			# usual group: currently unavaiilable
			self.information("Join Group Chat", "This type of group is currently N/A")
		
	def showConnectDialog(self):
		# opens connection dialog		
		QDialog.__init__(self)
		self.connectionDialog = uic.loadUi(PATH_UI_CONNECTION)
		self.connectionDialog.show()
		self.connect(self.connectionDialog, SIGNAL("accepted()"), self.connection)
		
		self.connectionDialog.eln_jid.setText(self.settings.value("jid", ""))
		self.connectionDialog.eln_pass.setText(self.settings.value("password", ""))

	def closeEvent(self, event):
		# called on close (Ctrl+Q)
		reply = QMessageBox.question(self, app.translate("wnd_main", "Exit"),
			app.translate("wnd_main", "Are you sure to quit?"), 
			QMessageBox.Yes | QMessageBox.No, 
			QMessageBox.No)
			
		if reply == QMessageBox.Yes:			
			try:
				sys.exit(self.helpForm)
			except AttributeError:
				pass
			self.disconnect()
			event.accept()
		else:
			event.ignore()

	def quitApp(self):
		self.disconnect()
		QApplication.instance().quit()

	def disconnect(self):
		if self.im:
			self.im.stop()
			self.im = None
			self.BuddyList.clear()
			self.act_connection.setEnabled(True)
			self.act_deconnection.setEnabled(False)
			self.eln_status_edit.hide()
			self.cmb_status_box.setCurrentIndex(5)
			self.cmb_status_box.setEnabled(False)
			self.act_away_buddies.setEnabled(False)
			self.act_offline_buddies.setEnabled(False)
			self.act_join_group_chat.setEnabled(False)

	def connection(self):		
		# settings for jid and pass
		self.settings.setValue("jid", self.connectionDialog.eln_jid.text())
		self.settings.setValue("password", self.connectionDialog.eln_pass.text())
			
		# latest status and show
		self.clientJid = str(self.connectionDialog.eln_jid.text())
		self.settings.beginGroup(self.clientJid)
		self.latestShow = self.settings.value("latestShow", "") # text as in SHOW
		self.latestStatus = self.settings.value("latestStatus", "")
		self.settings.endGroup()
			
		# starting xmpp thread
		self.im = Client(self.connectionDialog.eln_jid.text(), self.connectionDialog.eln_pass.text(),
			self.latestShow, self.latestStatus)
		self.im.start()
			
		self.cmb_status_box.setItemText(5, "Please wait...")
			
		# connecting signals
		self.connect(self.im, SIGNAL("sessionStarted(PyQt_PyObject)"), self.sessionStarted)
		self.connect(self.im, SIGNAL("presence(PyQt_PyObject)"), self.BuddyList.presence)
		self.connect(self.im, SIGNAL("disconnect"), self.disconnect)
		self.connect(self.im, SIGNAL("message"), self.BuddyList.message)
		self.connect(self.im, SIGNAL("messageMUC"), self.BuddyList.messageMUC)
		self.connect(self.im, SIGNAL("inviteMUC"), self.inviteMUC)
		self.connect(self.im, SIGNAL("critical"), self.critical)
		self.connect(self.im, SIGNAL("information"), self.information)
		self.connect(self.im, SIGNAL("debug"), self.debug)
		
	def sessionStarted(self, roster_keys):
		self.act_connection.setEnabled(False)
		self.act_deconnection.setEnabled(True)
		self.act_join_group_chat.setEnabled(True)
		self.act_away_buddies.setEnabled(True)
		self.act_offline_buddies.setEnabled(True)
        
		# construct contact list	
		self.BuddyList.setConnection(self.im)
		#store roster in settings
		self.settings.beginGroup(self.clientJid)
		self.settings.setValue("roster", roster_keys)
		self.settings.endGroup()
		self.BuddyList.constructList(roster_keys)
		self.showAwayBuddies()
		self.showOfflineBuddies()
	
		# restore show and status
		self.eln_status_edit.show()
		self.eln_status_edit.setText(self.latestStatus)
		
		self.cmb_status_box.setItemText(5, "Offline")
		if self.latestShow == "": self.cmb_status_box.setCurrentIndex(SHOW.index('available'))
		else: self.cmb_status_box.setCurrentIndex(SHOW.index(self.latestShow))
		self.cmb_status_box.setEnabled(True)
	
	def statusUpdate(self):
		if SHOW[self.cmb_status_box.currentIndex()] != "offline":
			# update settings
			self.settings.beginGroup(self.clientJid)
			self.settings.setValue("latestShow", SHOW[self.cmb_status_box.currentIndex()])
			self.settings.setValue("latestStatus", self.eln_status_edit.text())
			self.settings.endGroup()
			self.debug("new presence set. show: '" + SHOW[self.cmb_status_box.currentIndex()] +
				"'; status: '" + self.eln_status_edit.text() + "'\n\n")
			
		self.im.changeStatus(self.cmb_status_box.currentIndex(), self.eln_status_edit.text())
            
	def showLogs(self):
		self.logsWidget.show()
		self.logsWidget.raise_()
		
	def debug(self, message):
		self.logsWidget.etx_logs.append(datetime.datetime.now().strftime("[%H:%M:%S]")+":\n" + message)
	
	def showAwayBuddies(self):	
		self.BuddyList.showAwayBuddies(not self.act_away_buddies.isChecked())
		
	def showOfflineBuddies(self):
		self.BuddyList.showOfflineBuddies(not self.act_offline_buddies.isChecked())
	
	def critical(self, title, content):
		QMessageBox.critical(self, title, content, QMessageBox.Ok)
		
	def information(self, title, content):
		QMessageBox.information(self, title, content, QMessageBox.Ok)
	
if __name__ == "__main__":
	# Setup logging
	logging.basicConfig(level=logging.DEBUG, format='%(levelname)-8s %(message)s')
	
	app = QApplication(sys.argv)
	window = MainWindow()
	window.show()
	sys.exit(app.exec_())
