
import logging
import time
import bs4
import WebRequest

from autotriever.util.Mailinator import MailinatorClient
from . import PreemptProcessorBase

class StoriesOnlineFetch(PreemptProcessorBase.PreemptProcessorBase):

	log_name = "Main.Processor.StoriesOnline"

	@staticmethod
	def wants_url(lowerspliturl, mimetype):
		return False

	@staticmethod
	def preemptive_wants_url(lowerspliturl:tuple):
		return False


	def activate_account(self, mc, mailid):
		self.log.info("Received account validation mail. Validating.")
		mail = mc.get_mail(mailid)

		soup = bs4.BeautifulSoup(mail, "lxml")
		assert soup.a
		assert "https://storiesonline.net/user/activate.php?token=" in soup.a['href']

		activateurl = soup.a['href']

		activatepage = self.wg.getpage(activateurl)
		soup = bs4.BeautifulSoup(activatepage, "lxml")
		tok = soup.find("input", attrs={'name' : 'token'})

		assert tok is not None

		postdata = {
			"token"  : tok['value'],
			"upass1" : mc.get_pseudo_pass(),
			"upass2" : mc.get_pseudo_pass(),
			"cmd"    : "Create Account"
			}

		logged_in = self.wg.getpage('https://storiesonline.net/user/activate.php', postData = postdata)

		self.log.info("Activation submitted. Checking account was created successfully.")
		soup = bs4.BeautifulSoup(logged_in, "lxml")

		for item in soup.find_all("span", class_='pane-head-text'):
			if mc.get_prefix() in item.get_text():
				self.log.info("Logged in successfully!")
				return

		raise ValueError("Failed to create an account!")
		# print(soup.a)

	def renew_account(self):
		self.log.info("Creating account.")
		mc = MailinatorClient()
		email = mc.get_address()
		pwd = mc.get_pseudo_pass()

		self.wg.getpage('https://storiesonline.net/user/new.php')
		postdata = {
			"email1" : email,
			"email2" : email,
			"cmd"    : "Send Me Invitation"
		}
		succ = self.wg.getpage("https://storiesonline.net/user/new.php", postData=postdata)
		if not "An account creation link has been emailed to you. Please, check your email and follow those simple instructions to create an account" in succ:
			raise ValueError("Couldn't create a account?")


		waited = 0

		self.log.info("Account created. Waiting for activation e-mail.")
		while 1:
			have = mc.get_available_inbox()
			for item in have:
				# print(item)
				if "subject" in item and item['subject'] == 'Storiesonline Account Activation Information':
					self.activate_account(mc, item['id'])
					return

			time.sleep(5)
			waited += 1
			if waited > 20:
				raise ValueError("Could not create an account?")

	def getpage(self, *args, **kwargs):
		while 1:
			ret = self.wg.getpage(*args, **kwargs)
			if "Access to unlinked chapters requires you to" in ret:
				self.renew_account()
			elif "Sorry! You have reached your daily limit of 16 stories per day" in ret:
				self.renew_account()
			else:
				break
		return ret

	def getFileAndName(self, *args, **kwargs):
		return self.wg.getpage(*args, **kwargs)

if __name__ == "__main__":

	import deps.logSetup
	deps.logSetup.initLogging()

	so = StoriesOnlineFetch()
	so.renew_account()