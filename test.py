
# This has to go first because of monkeypatching in local_entry_point
from autotriever import local_entry_point # noqa

import sys
import logging
import json
import threading

from selenium import webdriver
import selenium.webdriver.chrome.service
import selenium.webdriver.chrome.options
import WebRequest

import autotriever.deps.logSetup
import autotriever.plugin_loader
from autotriever import dispatcher

QIDIAN_TEST_META = {
	'https://www.webnovel.com/rssbook/15618689806357905/44660325517149986/Stubborn-Love-of-a-Roguish-Scion/HuntingSYMP, Chapter 90': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Stubborn Love of a Roguish Scion',
		'resolved_url': 'https://www.webnovel.com/book/15618689806357905/44660325517149986/Stubborn-Love-of-a-Roguish-Scion/Hunting'
	},
	'https://www.webnovel.com/rssbook/8041181106002905/40090868723532875/Warlord-of-Chaos/CelebritiesWOC, Chapter 184': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Warlord of Chaos',
		'resolved_url': 'https://www.webnovel.com/book/8041181106002905/40090868723532875/Warlord-of-Chaos/Celebrities'
	},
	'https://www.webnovel.com/rssbook/10442141605034505/41628651162227836/The-Great-Worm-Lich/New-York’s-BelieverTGWL, Chapter 621': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'The Great Worm Lich',
		'resolved_url': 'https://www.webnovel.com/book/10442141605034505/41628651162227836/The-Great-Worm-Lich/New-York%E2%80%99s-Believer'
	},
	'https://www.webnovel.com/rssbook/13888929406066105/44790002374205489/Benua-Pertarungan-2:-Sekte-Tang-Yang-Tiada-Bandingannya/Aku-Tidak-Peduli,-Aku-Cinta-KauBP2:STYTB, Chapter 372': {
		'type': 'translated',
		'ad_free': False,
		'language': 'in',
		'series_name': 'Benua Pertarungan 2: Sekte Tang Yang Tiada Bandingannya',
		'resolved_url': 'https://www.webnovel.com/book/13888929406066105/44790002374205489/Benua-Pertarungan-2%3A-Sekte-Tang-Yang-Tiada-Bandingannya/Aku-Tidak-Peduli%2C-Aku-Cinta-Kau'
	},
	'https://www.webnovel.com/rssbook/16523857005254305/44847670631655521/Cultivation-Taobao-Store/Chapter-190---Xiao-You-adventure-(3), Chapter 190': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Cultivation Taobao Store',
		'resolved_url': 'https://www.webnovel.com/book/16523857005254305/44847670631655521/Cultivation-Taobao-Store/Chapter-190---Xiao-You-adventure-(3)'
	},
	'https://www.webnovel.com/rssbook/16523857005254305/44847580437335724/Cultivation-Taobao-Store/Chapter-188---Xiao-You-adventure-(1), Chapter 188': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Cultivation Taobao Store',
		'resolved_url': 'https://www.webnovel.com/book/16523857005254305/44847580437335724/Cultivation-Taobao-Store/Chapter-188---Xiao-You-adventure-(1)'
	},
	'https://www.webnovel.com/rssbook/16523857005254305/44847623135354101/Cultivation-Taobao-Store/Chapter-189---Xiao-You-adventure-(2), Chapter 189': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Cultivation Taobao Store',
		'resolved_url': 'https://www.webnovel.com/book/16523857005254305/44847623135354101/Cultivation-Taobao-Store/Chapter-189---Xiao-You-adventure-(2)'
	},
	'https://www.webnovel.com/rssbook/16523709605253705/44847448652311346/Kung-Fu-Beyond-the-World/Chapter-378---Kill-without-mercy, Chapter 378': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Kung Fu Beyond the World',
		'resolved_url': 'https://www.webnovel.com/book/16523709605253705/44847448652311346/Kung-Fu-Beyond-the-World/Chapter-378---Kill-without-mercy'
	},
	'https://www.webnovel.com/rssbook/16523709605253705/44847404092025194/Kung-Fu-Beyond-the-World/Chapter-376---The-village-suddenly-became-rich, Chapter 376': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Kung Fu Beyond the World',
		'resolved_url': 'https://www.webnovel.com/book/16523709605253705/44847404092025194/Kung-Fu-Beyond-the-World/Chapter-376---The-village-suddenly-became-rich'
	},
	'https://www.webnovel.com/rssbook/16523709605253705/44847427445910115/Kung-Fu-Beyond-the-World/Chapter-377---Land-Pangolin-God, Chapter 377': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Kung Fu Beyond the World',
		'resolved_url': 'https://www.webnovel.com/book/16523709605253705/44847427445910115/Kung-Fu-Beyond-the-World/Chapter-377---Land-Pangolin-God'
	},
	'https://www.webnovel.com/rssbook/15618689806357905/44660325248714528/Stubborn-Love-of-a-Roguish-Scion/Sister-In-LawSYMP, Chapter 89': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Stubborn Love of a Roguish Scion',
		'resolved_url': 'https://www.webnovel.com/book/15618689806357905/44660325248714528/Stubborn-Love-of-a-Roguish-Scion/Sister-In-Law'
	},
	'https://www.webnovel.com/rssbook/10442141605034505/41628598028782281/The-Great-Worm-Lich/The-InvadersTGWL, Chapter 620': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'The Great Worm Lich',
		'resolved_url': 'https://www.webnovel.com/book/10442141605034505/41628598028782281/The-Great-Worm-Lich/The-Invaders'
	},
	"https://www.webnovel.com/rssbook/9087070605001805/32970117889452466/Warrior's-Promise/Jade-Cloud-Lake-in-Central-Continent,-I'm-waiting-for-you!AWP, Chapter 967": {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': "Warrior's Promise",
		'resolved_url': 'https://www.webnovel.com/book/9087070605001805/32970117889452466/Warrior&#39;s-Promise/Jade-Cloud-Lake-in-Central-Continent%2C-I&#39;m-waiting-for-you!'
	},
	'https://www.webnovel.com/rssbook/12905356906949105/41078404111463170/The-Bumpy-Road-of-Marriage:-The-Ex-Wife-Is-Expecting/The-Father-Of-My-ChildEWE, Chapter 354': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'The Bumpy Road of Marriage: The Ex-Wife Is Expecting',
		'resolved_url': 'https://www.webnovel.com/book/12905356906949105/41078404111463170/The-Bumpy-Road-of-Marriage%3A-The-Ex-Wife-Is-Expecting/The-Father-Of-My-Child'
	},
	'https://www.webnovel.com/rssbook/13772664505174105/42534718805172760/Sword-Among-Us/The-Dungeon-of-the-Royal-MansionSAU, Chapter 490': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Sword Among Us',
		'resolved_url': 'https://www.webnovel.com/book/13772664505174105/42534718805172760/Sword-Among-Us/The-Dungeon-of-the-Royal-Mansion'
	},
	'https://www.webnovel.com/rssbook/12905356906949105/41077414675148003/The-Bumpy-Road-of-Marriage:-The-Ex-Wife-Is-Expecting/But-You-Love-HimEWE, Chapter 353': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'The Bumpy Road of Marriage: The Ex-Wife Is Expecting',
		'resolved_url': 'https://www.webnovel.com/book/12905356906949105/41077414675148003/The-Bumpy-Road-of-Marriage%3A-The-Ex-Wife-Is-Expecting/But-You-Love-Him'
	},
	'https://www.webnovel.com/rssbook/13373465406646405/42235400118401449/Good-Morning,-Mister-Dragon!/Don’t-Look-at-Her,-She’s-Not-a-Good-PersonGMMD, Chapter 506': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Good Morning, Mister Dragon!',
		'resolved_url': 'https://www.webnovel.com/book/13373465406646405/42235400118401449/Good-Morning%2C-Mister-Dragon!/Don%E2%80%99t-Look-at-Her%2C-She%E2%80%99s-Not-a-Good-Person'
	},
	'https://www.webnovel.com/rssbook/14011317605955805/44792692365907869/The-Sweetest-Medicine/A-Threat:-I-Want-You-To-Help-MeTSM, Chapter 439': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'The Sweetest Medicine',
		'resolved_url': 'https://www.webnovel.com/book/14011317605955805/44792692365907869/The-Sweetest-Medicine/A-Threat%3A-I-Want-You-To-Help-Me'
	},
	'https://www.webnovel.com/rssbook/11660247905469805/40154804143585753/Nano-Machine-(Retranslated-Version)/266-Night-in-the-Inn-(2), Chapter 266': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Nano Machine (Retranslated Version)',
		'resolved_url': 'https://www.webnovel.com/book/11660247905469805/40154804143585753/Nano-Machine-(Retranslated-Version)/266-Night-in-the-Inn-(2)'
	},
	'https://www.webnovel.com/rssbook/14374767306223005/41614469180213818/Descent-of-the-Demon-God/Emergency-Shareholder-Meeting-(5), Chapter 132': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Descent of the Demon God',
		'resolved_url': 'https://www.webnovel.com/book/14374767306223005/41614469180213818/Descent-of-the-Demon-God/Emergency-Shareholder-Meeting-(5)'
	},
	'https://www.webnovel.com/rssbook/13311963706454205/44860504816024723/Story-of-a-Big-Player-from-Gangnam/Expanding-Logistics-Business-into-Overseas-Market-(2)-–-Part-1, Chapter 456': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Story of a Big Player from Gangnam',
		'resolved_url': 'https://www.webnovel.com/book/13311963706454205/44860504816024723/Story-of-a-Big-Player-from-Gangnam/Expanding-Logistics-Business-into-Overseas-Market-(2)-%E2%80%93-Part-1'
	},
	'https://www.webnovel.com/rssbook/11954071206653305/44813471149257023/Empire-of-the-Ring/A-Battle-(2), Chapter 733': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Empire of the Ring',
		'resolved_url': 'https://www.webnovel.com/book/11954071206653305/44813471149257023/Empire-of-the-Ring/A-Battle-(2)'
	},
	'https://www.webnovel.com/rssbook/11954071206653305/44793100136151285/Empire-of-the-Ring/A-Battle-(1), Chapter 732': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Empire of the Ring',
		'resolved_url': 'https://www.webnovel.com/book/11954071206653305/44793100136151285/Empire-of-the-Ring/A-Battle-(1)'
	},
	'https://www.webnovel.com/rssbook/14374767306223005/41614465690552886/Descent-of-the-Demon-God/Emergency-Shareholder-Meeting-(4), Chapter 131': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Descent of the Demon God',
		'resolved_url': 'https://www.webnovel.com/book/14374767306223005/41614465690552886/Descent-of-the-Demon-God/Emergency-Shareholder-Meeting-(4)'
	},
	'https://www.webnovel.com/rssbook/13311963706454205/44820370208903625/Story-of-a-Big-Player-from-Gangnam/Expanding-Logistics-Business-into-Overseas-Market-(1)-–-Part-2, Chapter 455': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Story of a Big Player from Gangnam',
		'resolved_url': 'https://www.webnovel.com/book/13311963706454205/44820370208903625/Story-of-a-Big-Player-from-Gangnam/Expanding-Logistics-Business-into-Overseas-Market-(1)-%E2%80%93-Part-2'
	},
	'https://www.webnovel.com/rssbook/14591197806945805/44849066496016529/Emperor-of-Steel/Gigant-Development-4, Chapter 315': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Emperor of Steel',
		'resolved_url': 'https://www.webnovel.com/book/14591197806945805/44849066496016529/Emperor-of-Steel/Gigant-Development-4'
	},
	'https://www.webnovel.com/rssbook/14591197806945805/44849031599423317/Emperor-of-Steel/Gigant-Development-3, Chapter 314': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Emperor of Steel',
		'resolved_url': 'https://www.webnovel.com/book/14591197806945805/44849031599423317/Emperor-of-Steel/Gigant-Development-3'
	},
	'https://www.webnovel.com/rssbook/11022733006234505/43764545646281681/Lord-of-the-Mysteries/Traveling-NotebookLoM, Chapter 1112': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Lord of the Mysteries',
		'resolved_url': 'https://www.webnovel.com/book/11022733006234505/43764545646281681/Lord-of-the-Mysteries/Traveling-Notebook'
	},
	'https://www.webnovel.com/rssbook/14009364006015205/44853216524953736/The-Law-of-Webnovels/Chapter-253, Chapter 253': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'The Law of Webnovels',
		'resolved_url': 'https://www.webnovel.com/book/14009364006015205/44853216524953736/The-Law-of-Webnovels/Chapter-253'
	},
	'https://www.webnovel.com/rssbook/14009364006015205/44853204445358079/The-Law-of-Webnovels/Chapter-252, Chapter 252': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'The Law of Webnovels',
		'resolved_url': 'https://www.webnovel.com/book/14009364006015205/44853204445358079/The-Law-of-Webnovels/Chapter-252'
	},
	'https://www.webnovel.com/rssbook/14009364006015205/44853192617415043/The-Law-of-Webnovels/Chapter-251, Chapter 251': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'The Law of Webnovels',
		'resolved_url': 'https://www.webnovel.com/book/14009364006015205/44853192617415043/The-Law-of-Webnovels/Chapter-251'
	},
	'https://www.webnovel.com/rssbook/14107168305361805/44844423636372247/Soul-Land-IV-(Douluo-Dalu)-:-Ultimate-Fighting/Bing-TianliangSLIV, Chapter 189': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Soul Land IV (Douluo Dalu) : Ultimate Fighting',
		'resolved_url': 'https://www.webnovel.com/book/14107168305361805/44844423636372247/Soul-Land-IV-(Douluo-Dalu)-%3A-Ultimate-Fighting/Bing-Tianliang'
	},
	'https://www.webnovel.com/rssbook/7853880705001905/36153955956345992/Pursuit-of-the-Truth/Beyond-Ancient-Zang-SkiesPoT, Chapter 1477': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Pursuit of the Truth',
		'resolved_url': 'https://www.webnovel.com/book/7853880705001905/36153955956345992/Pursuit-of-the-Truth/Beyond-Ancient-Zang-Skies'
	},
	'https://www.webnovel.com/rssbook/7853880705001905/36153950033989557/Pursuit-of-the-Truth/My-Thirty-SkiesPoT, Chapter 1476': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Pursuit of the Truth',
		'resolved_url': 'https://www.webnovel.com/book/7853880705001905/36153950033989557/Pursuit-of-the-Truth/My-Thirty-Skies'
	},
	'https://www.webnovel.com/rssbook/13769162806201605/42640561026429482/Game-thủ-mang-tên-Thành-phố-dưới-lòng-đất/Chương-475:-Đội-ngũ-cứu-việnGNUG, Chapter 473': {
		'type': 'translated',
		'ad_free': True,
		'language': 'vi',
		'series_name': 'Game thủ mang tên Thành phố dưới lòng đất',
		'resolved_url': 'https://www.webnovel.com/book/13769162806201605/42640561026429482/Game-th%E1%BB%A7-mang-t%C3%AAn-Th%C3%A0nh-ph%E1%BB%91-d%C6%B0%E1%BB%9Bi-l%C3%B2ng-%C4%91%E1%BA%A5t/Ch%C6%B0%C6%A1ng-475%3A-%C4%90%E1%BB%99i-ng%C5%A9-c%E1%BB%A9u-vi%E1%BB%87n'
	},
	'https://www.webnovel.com/rssbook/13769162806201605/42640560221123105/Game-thủ-mang-tên-Thành-phố-dưới-lòng-đất/Chương-474:-Những-người-này-bị-bệnh-tâm-thần-à!-GNUG, Chapter 472': {
		'type': 'translated',
		'ad_free': True,
		'language': 'vi',
		'series_name': 'Game thủ mang tên Thành phố dưới lòng đất',
		'resolved_url': 'https://www.webnovel.com/book/13769162806201605/42640560221123105/Game-th%E1%BB%A7-mang-t%C3%AAn-Th%C3%A0nh-ph%E1%BB%91-d%C6%B0%E1%BB%9Bi-l%C3%B2ng-%C4%91%E1%BA%A5t/Ch%C6%B0%C6%A1ng-474%3A-Nh%E1%BB%AFng-ng%C6%B0%E1%BB%9Di-n%C3%A0y-b%E1%BB%8B-b%E1%BB%87nh-t%C3%A2m-th%E1%BA%A7n-%C3%A0!-'
	},
	'https://www.webnovel.com/rssbook/13888929406066105/40205847430757151/Benua-Pertarungan-2:-Sekte-Tang-Yang-Tiada-Bandingannya/Permaisuri-Es-TerbangunBP2:STYTB, Chapter 98': {
		'type': 'translated',
		'ad_free': False,
		'language': 'in',
		'series_name': 'Benua Pertarungan 2: Sekte Tang Yang Tiada Bandingannya',
		'resolved_url': 'https://www.webnovel.com/book/13888929406066105/40205847430757151/Benua-Pertarungan-2%3A-Sekte-Tang-Yang-Tiada-Bandingannya/Permaisuri-Es-Terbangun'
	},
	'https://www.webnovel.com/rssbook/13888929406066105/40205826492786477/Benua-Pertarungan-2:-Sekte-Tang-Yang-Tiada-Bandingannya/Menerobos-Penjara,-Penguasa-Es-AbadiBP2:STYTB, Chapter 97': {
		'type': 'translated',
		'ad_free': False,
		'language': 'in',
		'series_name': 'Benua Pertarungan 2: Sekte Tang Yang Tiada Bandingannya',
		'resolved_url': 'https://www.webnovel.com/book/13888929406066105/40205826492786477/Benua-Pertarungan-2%3A-Sekte-Tang-Yang-Tiada-Bandingannya/Menerobos-Penjara%2C-Penguasa-Es-Abadi'
	},
	'https://www.webnovel.com/rssbook/13888929406066105/40205805017949906/Benua-Pertarungan-2:-Sekte-Tang-Yang-Tiada-Bandingannya/Pertempuran-Penentuan-3-Lawan-3!BP2:STYTB, Chapter 96': {
		'type': 'translated',
		'ad_free': False,
		'language': 'in',
		'series_name': 'Benua Pertarungan 2: Sekte Tang Yang Tiada Bandingannya',
		'resolved_url': 'https://www.webnovel.com/book/13888929406066105/40205805017949906/Benua-Pertarungan-2%3A-Sekte-Tang-Yang-Tiada-Bandingannya/Pertempuran-Penentuan-3-Lawan-3!'
	},
	'https://www.webnovel.com/rssbook/13888929406066105/40205780858758672/Benua-Pertarungan-2:-Sekte-Tang-Yang-Tiada-Bandingannya/Kemuliaan-Shrek!BP2:STYTB, Chapter 95': {
		'type': 'translated',
		'ad_free': False,
		'language': 'in',
		'series_name': 'Benua Pertarungan 2: Sekte Tang Yang Tiada Bandingannya',
		'resolved_url': 'https://www.webnovel.com/book/13888929406066105/40205780858758672/Benua-Pertarungan-2%3A-Sekte-Tang-Yang-Tiada-Bandingannya/Kemuliaan-Shrek!'
	},
	'https://www.webnovel.com/rssbook/13769162806201605/42640551094317487/Game-thủ-mang-tên-Thành-phố-dưới-lòng-đất/Chương-473:-Chạy-trốn-GNUG, Chapter 471': {
		'type': 'translated',
		'ad_free': True,
		'language': 'vi',
		'series_name': 'Game thủ mang tên Thành phố dưới lòng đất',
		'resolved_url': 'https://www.webnovel.com/book/13769162806201605/42640551094317487/Game-th%E1%BB%A7-mang-t%C3%AAn-Th%C3%A0nh-ph%E1%BB%91-d%C6%B0%E1%BB%9Bi-l%C3%B2ng-%C4%91%E1%BA%A5t/Ch%C6%B0%C6%A1ng-473%3A-Ch%E1%BA%A1y-tr%E1%BB%91n-'
	},
	"https://www.webnovel.com/rssbook/8335483105000205/43802851385857243/The-Evil-Consort-Above-An-Evil-King/Aren't-You-Going-To-Blame-Me?-(3)VVC, Chapter 2895": {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'The Evil Consort Above An Evil King',
		'resolved_url': 'https://www.webnovel.com/book/8335483105000205/43802851385857243/The-Evil-Consort-Above-An-Evil-King/Aren&#39;t-You-Going-To-Blame-Me%3F-(3)'
	},
	"https://www.webnovel.com/rssbook/8335483105000205/43802820247351428/The-Evil-Consort-Above-An-Evil-King/Aren't-You-Going-To-Blame-Me?-(2)VVC, Chapter 2894": {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'The Evil Consort Above An Evil King',
		'resolved_url': 'https://www.webnovel.com/book/8335483105000205/43802820247351428/The-Evil-Consort-Above-An-Evil-King/Aren&#39;t-You-Going-To-Blame-Me%3F-(2)'
	},
	'https://www.webnovel.com/rssbook/7853880705001905/36013950491490052/Pursuit-of-the-Truth/Planting-a-PromisePoT, Chapter 1461': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Pursuit of the Truth',
		'resolved_url': 'https://www.webnovel.com/book/7853880705001905/36013950491490052/Pursuit-of-the-Truth/Planting-a-Promise'
	},
	'https://www.webnovel.com/rssbook/7853880705001905/36013900294058560/Pursuit-of-the-Truth/I’ll-Help-You!PoT, Chapter 1454': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Pursuit of the Truth',
		'resolved_url': 'https://www.webnovel.com/book/7853880705001905/36013900294058560/Pursuit-of-the-Truth/I%E2%80%99ll-Help-You!'
	},
	'https://www.webnovel.com/rssbook/11263692606307605/44551304734884289/The-Lord’s-Empire/Hu-XieTLE, Chapter 1593': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'The Lord’s Empire',
		'resolved_url': 'https://www.webnovel.com/book/11263692606307605/44551304734884289/The-Lord%E2%80%99s-Empire/Hu-Xie'
	},
	"https://www.webnovel.com/rssbook/8335483105000205/43802811925852175/The-Evil-Consort-Above-An-Evil-King/Aren't-You-Going-To-Blame-Me?VVC, Chapter 2893": {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'The Evil Consort Above An Evil King',
		'resolved_url': 'https://www.webnovel.com/book/8335483105000205/43802811925852175/The-Evil-Consort-Above-An-Evil-King/Aren&#39;t-You-Going-To-Blame-Me%3F'
	},
	'https://www.webnovel.com/rssbook/8335483105000205/43802799863029449/The-Evil-Consort-Above-An-Evil-King/Getting-Drunk-(3)VVC, Chapter 2892': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'The Evil Consort Above An Evil King',
		'resolved_url': 'https://www.webnovel.com/book/8335483105000205/43802799863029449/The-Evil-Consort-Above-An-Evil-King/Getting-Drunk-(3)'
	},
	"https://www.webnovel.com/rssbook/12905356906949105/41050641459639274/The-Bumpy-Road-of-Marriage:-The-Ex-Wife-Is-Expecting/The-Little-Darling's-DaddyEWE, Chapter 352": {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'The Bumpy Road of Marriage: The Ex-Wife Is Expecting',
		'resolved_url': 'https://www.webnovel.com/book/12905356906949105/41050641459639274/The-Bumpy-Road-of-Marriage%3A-The-Ex-Wife-Is-Expecting/The-Little-Darling&#39;s-Daddy'
	},
	'https://www.webnovel.com/rssbook/13888929406066105/40205758024966026/Benua-Pertarungan-2:-Sekte-Tang-Yang-Tiada-Bandingannya/Meriam-Perpaduan-Super-Yang-Putus-AsaBP2:STYTB, Chapter 94': {
		'type': 'translated',
		'ad_free': False,
		'language': 'in',
		'series_name': 'Benua Pertarungan 2: Sekte Tang Yang Tiada Bandingannya',
		'resolved_url': 'https://www.webnovel.com/book/13888929406066105/40205758024966026/Benua-Pertarungan-2%3A-Sekte-Tang-Yang-Tiada-Bandingannya/Meriam-Perpaduan-Super-Yang-Putus-Asa'
	},
	'https://www.webnovel.com/rssbook/13888929406066105/40205738177516042/Benua-Pertarungan-2:-Sekte-Tang-Yang-Tiada-Bandingannya/Kemuliaan-Shrek!BP2:STYTB, Chapter 93': {
		'type': 'translated',
		'ad_free': False,
		'language': 'in',
		'series_name': 'Benua Pertarungan 2: Sekte Tang Yang Tiada Bandingannya',
		'resolved_url': 'https://www.webnovel.com/book/13888929406066105/40205738177516042/Benua-Pertarungan-2%3A-Sekte-Tang-Yang-Tiada-Bandingannya/Kemuliaan-Shrek!'
	},
	'https://www.webnovel.com/rssbook/13888929406066105/40205713481453928/Benua-Pertarungan-2:-Sekte-Tang-Yang-Tiada-Bandingannya/Kebangunan-Dunia-BawahBP2:STYTB, Chapter 92': {
		'type': 'translated',
		'ad_free': False,
		'language': 'in',
		'series_name': 'Benua Pertarungan 2: Sekte Tang Yang Tiada Bandingannya',
		'resolved_url': 'https://www.webnovel.com/book/13888929406066105/40205713481453928/Benua-Pertarungan-2%3A-Sekte-Tang-Yang-Tiada-Bandingannya/Kebangunan-Dunia-Bawah'
	},
	'https://www.webnovel.com/rssbook/13888929406066105/40205696033149167/Benua-Pertarungan-2:-Sekte-Tang-Yang-Tiada-Bandingannya/Pertempuran-PenentuanBP2:STYTB, Chapter 91': {
		'type': 'translated',
		'ad_free': False,
		'language': 'in',
		'series_name': 'Benua Pertarungan 2: Sekte Tang Yang Tiada Bandingannya',
		'resolved_url': 'https://www.webnovel.com/book/13888929406066105/40205696033149167/Benua-Pertarungan-2%3A-Sekte-Tang-Yang-Tiada-Bandingannya/Pertempuran-Penentuan'
	},
	'https://www.webnovel.com/rssbook/15532164606886805/44475026400934653/Evil-Awe-Inspiring/Despise-a-hundred-times, Chapter 92': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Evil Awe-Inspiring',
		'resolved_url': 'https://www.webnovel.com/book/15532164606886805/44475026400934653/Evil-Awe-Inspiring/Despise-a-hundred-times'
	},
	'https://www.webnovel.com/rssbook/11022730305240505/41617417960488616/Ninth-In-the-World/Need-To-Learn-How-To-Be-an-Eloquent-Speaker-FirstNITW, Chapter 444': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Ninth In the World',
		'resolved_url': 'https://www.webnovel.com/book/11022730305240505/41617417960488616/Ninth-In-the-World/Need-To-Learn-How-To-Be-an-Eloquent-Speaker-First'
	},
	"https://www.webnovel.com/rssbook/13976997305757105/39467379075367926/Invincible-Divine-Dragon's-Cultivation-System/The-Female-Light-Divine-DragonIDDCS, Chapter 222": {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': "Invincible Divine Dragon's Cultivation System",
		'resolved_url': 'https://www.webnovel.com/book/13976997305757105/39467379075367926/Invincible-Divine-Dragon&#39;s-Cultivation-System/The-Female-Light-Divine-Dragon'
	},
	"https://www.webnovel.com/rssbook/13976997305757105/39467390618092622/Invincible-Divine-Dragon's-Cultivation-System/Progenitor-Tree-IDDCS, Chapter 223": {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': "Invincible Divine Dragon's Cultivation System",
		'resolved_url': 'https://www.webnovel.com/book/13976997305757105/39467390618092622/Invincible-Divine-Dragon&#39;s-Cultivation-System/Progenitor-Tree-'
	},
	"https://www.webnovel.com/rssbook/13976997305757105/39467376391013349/Invincible-Divine-Dragon's-Cultivation-System/Glowing-Like-a-Goddess-IDDCS, Chapter 221": {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': "Invincible Divine Dragon's Cultivation System",
		'resolved_url': 'https://www.webnovel.com/book/13976997305757105/39467376391013349/Invincible-Divine-Dragon&#39;s-Cultivation-System/Glowing-Like-a-Goddess-'
	},
	'https://www.webnovel.com/rssbook/14045471906194905/44007897167878872/League-of-Legends:-League-of-Unknowns/The-Incredible-Middle-lanerLOU, Chapter 401': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'League of Legends: League of Unknowns',
		'resolved_url': 'https://www.webnovel.com/book/14045471906194905/44007897167878872/League-of-Legends%3A-League-of-Unknowns/The-Incredible-Middle-laner'
	},
	'https://www.webnovel.com/rssbook/14045471906194905/44007899583798007/League-of-Legends:-League-of-Unknowns/Battle-of-the-RichesLOU, Chapter 402': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'League of Legends: League of Unknowns',
		'resolved_url': 'https://www.webnovel.com/book/14045471906194905/44007899583798007/League-of-Legends%3A-League-of-Unknowns/Battle-of-the-Riches'
	},
	'https://www.webnovel.com/rssbook/14045471906194905/44007902788250794/League-of-Legends:-League-of-Unknowns/Vayne-is-BannedLOU, Chapter 403': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'League of Legends: League of Unknowns',
		'resolved_url': 'https://www.webnovel.com/book/14045471906194905/44007902788250794/League-of-Legends%3A-League-of-Unknowns/Vayne-is-Banned'
	},
	"https://www.webnovel.com/rssbook/6838665602002105/44065300731195667/A-Sorcerer's-Journey/Myna-the-TutorASJ, Chapter 546": {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': "A Sorcerer's Journey",
		'resolved_url': 'https://www.webnovel.com/book/6838665602002105/44065300731195667/A-Sorcerer&#39;s-Journey/Myna-the-Tutor'
	},
	"https://www.webnovel.com/rssbook/6838665602002105/44065304237629736/A-Sorcerer's-Journey/Muyi-the-Greatsword-SlayerASJ, Chapter 547": {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': "A Sorcerer's Journey",
		'resolved_url': 'https://www.webnovel.com/book/6838665602002105/44065304237629736/A-Sorcerer&#39;s-Journey/Muyi-the-Greatsword-Slayer'
	},
	"https://www.webnovel.com/rssbook/6838665602002105/44077220355955329/A-Sorcerer's-Journey/The-Workshop-FactoryASJ, Chapter 548": {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': "A Sorcerer's Journey",
		'resolved_url': 'https://www.webnovel.com/book/6838665602002105/44077220355955329/A-Sorcerer&#39;s-Journey/The-Workshop-Factory'
	},
	'https://www.webnovel.com/rssbook/12266174706182005/44406596280829060/Top-Sexy-Girl-Group/Chapter-125:-The-Battle-on-the-Tubes, Chapter 125': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Top Sexy Girl Group',
		'resolved_url': 'https://www.webnovel.com/book/12266174706182005/44406596280829060/Top-Sexy-Girl-Group/Chapter-125%3A-The-Battle-on-the-Tubes'
	},
	'https://www.webnovel.com/rssbook/13888929406066105/40205661136551076/Benua-Pertarungan-2:-Sekte-Tang-Yang-Tiada-Bandingannya/Gila-akan-ShrekBP2:STYTB, Chapter 90': {
		'type': 'translated',
		'ad_free': False,
		'language': 'in',
		'series_name': 'Benua Pertarungan 2: Sekte Tang Yang Tiada Bandingannya',
		'resolved_url': 'https://www.webnovel.com/book/13888929406066105/40205661136551076/Benua-Pertarungan-2%3A-Sekte-Tang-Yang-Tiada-Bandingannya/Gila-akan-Shrek'
	},
	'https://www.webnovel.com/rssbook/11022730305240505/41617417675262075/Ninth-In-the-World/Yin-Wushang-Retreats,-The-Killing-Array-Is-ActivatedNITW, Chapter 442': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Ninth In the World',
		'resolved_url': 'https://www.webnovel.com/book/11022730305240505/41617417675262075/Ninth-In-the-World/Yin-Wushang-Retreats%2C-The-Killing-Array-Is-Activated'
	},
	'https://www.webnovel.com/rssbook/11022730305240505/41617417943697533/Ninth-In-the-World/A-Fleeting-MomentNITW, Chapter 443': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Ninth In the World',
		'resolved_url': 'https://www.webnovel.com/book/11022730305240505/41617417943697533/Ninth-In-the-World/A-Fleeting-Moment'
	},
	"https://www.webnovel.com/rssbook/6838665602002105/44064456233244474/A-Sorcerer's-Journey/RejectedASJ, Chapter 544": {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': "A Sorcerer's Journey",
		'resolved_url': 'https://www.webnovel.com/book/6838665602002105/44064456233244474/A-Sorcerer&#39;s-Journey/Rejected'
	},
	"https://www.webnovel.com/rssbook/6838665602002105/44064466165356439/A-Sorcerer's-Journey/The-Origins-of-SorcerersASJ, Chapter 545": {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': "A Sorcerer's Journey",
		'resolved_url': 'https://www.webnovel.com/book/6838665602002105/44064466165356439/A-Sorcerer&#39;s-Journey/The-Origins-of-Sorcerers'
	},
	"https://www.webnovel.com/rssbook/13976997305757105/39467367247433013/Invincible-Divine-Dragon's-Cultivation-System/Can't-Afford-To-Offend,-Can't-Afford-To-OffendIDDCS, Chapter 220": {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': "Invincible Divine Dragon's Cultivation System",
		'resolved_url': 'https://www.webnovel.com/book/13976997305757105/39467367247433013/Invincible-Divine-Dragon&#39;s-Cultivation-System/Can&#39;t-Afford-To-Offend%2C-Can&#39;t-Afford-To-Offend'
	},
	'https://www.webnovel.com/rssbook/14045471906194905/44007893409782454/League-of-Legends:-League-of-Unknowns/A-Challenge-from-NoxusLOU, Chapter 400': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'League of Legends: League of Unknowns',
		'resolved_url': 'https://www.webnovel.com/book/14045471906194905/44007893409782454/League-of-Legends%3A-League-of-Unknowns/A-Challenge-from-Noxus'
	},
	'https://www.webnovel.com/rssbook/14045471906194905/44007874350864842/League-of-Legends:-League-of-Unknowns/Number-OneLOU, Chapter 399': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'League of Legends: League of Unknowns',
		'resolved_url': 'https://www.webnovel.com/book/14045471906194905/44007874350864842/League-of-Legends%3A-League-of-Unknowns/Number-One'
	},
	'https://www.webnovel.com/rssbook/11022730305240505/41617417692053158/Ninth-In-the-World/The-Peace-HotelNITW, Chapter 441': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Ninth In the World',
		'resolved_url': 'https://www.webnovel.com/book/11022730305240505/41617417692053158/Ninth-In-the-World/The-Peace-Hotel'
	},
	'https://www.webnovel.com/rssbook/11022730305240505/41617417423617701/Ninth-In-the-World/We-Can-Only-Go-Somewhere-ElseNITW, Chapter 440': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Ninth In the World',
		'resolved_url': 'https://www.webnovel.com/book/11022730305240505/41617417423617701/Ninth-In-the-World/We-Can-Only-Go-Somewhere-Else'
	},
	"https://www.webnovel.com/rssbook/13976997305757105/39467364848303491/Invincible-Divine-Dragon's-Cultivation-System/Miracle-Doctor-Wang,-Please-Give-Me-Your-OrderIDDCS, Chapter 219": {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': "Invincible Divine Dragon's Cultivation System",
		'resolved_url': 'https://www.webnovel.com/book/13976997305757105/39467364848303491/Invincible-Divine-Dragon&#39;s-Cultivation-System/Miracle-Doctor-Wang%2C-Please-Give-Me-Your-Order'
	},
	'https://www.webnovel.com/rssbook/14045471906194905/44007870575995654/League-of-Legends:-League-of-Unknowns/Living-In-a-Hard-DriveLOU, Chapter 398': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'League of Legends: League of Unknowns',
		'resolved_url': 'https://www.webnovel.com/book/14045471906194905/44007870575995654/League-of-Legends%3A-League-of-Unknowns/Living-In-a-Hard-Drive'
	},
	'https://www.webnovel.com/rssbook/14045471906194905/44007865492503318/League-of-Legends:-League-of-Unknowns/Qi-Qiao’s-MentorLOU, Chapter 397': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'League of Legends: League of Unknowns',
		'resolved_url': 'https://www.webnovel.com/book/14045471906194905/44007865492503318/League-of-Legends%3A-League-of-Unknowns/Qi-Qiao%E2%80%99s-Mentor'
	},
	'https://www.webnovel.com/rssbook/13888929406066105/39508510634998498/Benua-Pertarungan-2:-Sekte-Tang-Yang-Tiada-Bandingannya/Asal-Mula-Kehancuran,-He-CaitouBP2:STYTB, Chapter 89': {
		'type': 'translated',
		'ad_free': False,
		'language': 'in',
		'series_name': 'Benua Pertarungan 2: Sekte Tang Yang Tiada Bandingannya',
		'resolved_url': 'https://www.webnovel.com/book/13888929406066105/39508510634998498/Benua-Pertarungan-2%3A-Sekte-Tang-Yang-Tiada-Bandingannya/Asal-Mula-Kehancuran%2C-He-Caitou'
	},
	'https://www.webnovel.com/rssbook/13587410505358405/44847179394772596/The-Emperor’s-Daughter/The-Emperor’s-Daughter-Chapter.-278, Chapter 278': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'The Emperor’s Daughter',
		'resolved_url': 'https://www.webnovel.com/book/13587410505358405/44847179394772596/The-Emperor%E2%80%99s-Daughter/The-Emperor%E2%80%99s-Daughter-Chapter.-278'
	},
	'https://www.webnovel.com/rssbook/13587410505358405/44847172147015222/The-Emperor’s-Daughter/The-Emperor’s-Daughter-Chapter.-277, Chapter 277': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'The Emperor’s Daughter',
		'resolved_url': 'https://www.webnovel.com/book/13587410505358405/44847172147015222/The-Emperor%E2%80%99s-Daughter/The-Emperor%E2%80%99s-Daughter-Chapter.-277'
	},
	'https://www.webnovel.com/rssbook/13888929406066105/39508492633032520/Benua-Pertarungan-2:-Sekte-Tang-Yang-Tiada-Bandingannya/Nyonya-Kembar-Api-dan-Es,-Tombak-Seribu-SeranganBP2:STYTB, Chapter 88': {
		'type': 'translated',
		'ad_free': False,
		'language': 'in',
		'series_name': 'Benua Pertarungan 2: Sekte Tang Yang Tiada Bandingannya',
		'resolved_url': 'https://www.webnovel.com/book/13888929406066105/39508492633032520/Benua-Pertarungan-2%3A-Sekte-Tang-Yang-Tiada-Bandingannya/Nyonya-Kembar-Api-dan-Es%2C-Tombak-Seribu-Serangan'
	},
	'https://www.webnovel.com/rssbook/13888929406066105/39508473305679561/Benua-Pertarungan-2:-Sekte-Tang-Yang-Tiada-Bandingannya/Emas-KehidupanBP2:STYTB, Chapter 87': {
		'type': 'translated',
		'ad_free': False,
		'language': 'in',
		'series_name': 'Benua Pertarungan 2: Sekte Tang Yang Tiada Bandingannya',
		'resolved_url': 'https://www.webnovel.com/book/13888929406066105/39508473305679561/Benua-Pertarungan-2%3A-Sekte-Tang-Yang-Tiada-Bandingannya/Emas-Kehidupan'
	},
	'https://www.webnovel.com/rssbook/8099443605005505/22860037890300944/The-Unrivaled-Tang-Sect/Perfect-Fusion,-The-Red-Soul-RingUTS, Chapter 44': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'The Unrivaled Tang Sect',
		'resolved_url': 'https://www.webnovel.com/book/8099443605005505/22860037890300944/The-Unrivaled-Tang-Sect/Perfect-Fusion%2C-The-Red-Soul-Ring'
	},
	'https://www.webnovel.com/rssbook/8099443605005505/22860095603923985/The-Unrivaled-Tang-Sect/You’re-Still-Alive?UTS, Chapter 45': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'The Unrivaled Tang Sect',
		'resolved_url': 'https://www.webnovel.com/book/8099443605005505/22860095603923985/The-Unrivaled-Tang-Sect/You%E2%80%99re-Still-Alive%3F'
	},
	'https://www.webnovel.com/rssbook/8099443605005505/22860122447469586/The-Unrivaled-Tang-Sect/The-Spirit-Eyes’-Second-Soul-SkillUTS, Chapter 46': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'The Unrivaled Tang Sect',
		'resolved_url': 'https://www.webnovel.com/book/8099443605005505/22860122447469586/The-Unrivaled-Tang-Sect/The-Spirit-Eyes%E2%80%99-Second-Soul-Skill'
	},
	'https://www.webnovel.com/rssbook/8099443605005505/22860227405732883/The-Unrivaled-Tang-Sect/The-Badge-of-a-Class-2-Soul-EngineerUTS, Chapter 47': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'The Unrivaled Tang Sect',
		'resolved_url': 'https://www.webnovel.com/book/8099443605005505/22860227405732883/The-Unrivaled-Tang-Sect/The-Badge-of-a-Class-2-Soul-Engineer'
	},
	'https://www.webnovel.com/rssbook/8099443605005505/28376011489999911/The-Unrivaled-Tang-Sect/A-Terrifying-Deterrence!UTS, Chapter 48': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'The Unrivaled Tang Sect',
		'resolved_url': 'https://www.webnovel.com/book/8099443605005505/28376011489999911/The-Unrivaled-Tang-Sect/A-Terrifying-Deterrence!'
	},
	'https://www.webnovel.com/rssbook/8099443605005505/28376161562182331/The-Unrivaled-Tang-Sect/The-Claw-of-the-Ice-Empress-UTS, Chapter 49': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'The Unrivaled Tang Sect',
		'resolved_url': 'https://www.webnovel.com/book/8099443605005505/28376161562182331/The-Unrivaled-Tang-Sect/The-Claw-of-the-Ice-Empress-'
	},
	'https://www.webnovel.com/rssbook/8099443605005505/28376312674581550/The-Unrivaled-Tang-Sect/Ancestor-Tang-San...UTS, Chapter 50': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'The Unrivaled Tang Sect',
		'resolved_url': 'https://www.webnovel.com/book/8099443605005505/28376312674581550/The-Unrivaled-Tang-Sect/Ancestor-Tang-San...'
	},
	'https://www.webnovel.com/rssbook/8099443605005505/28376344349965359/The-Unrivaled-Tang-Sect/The-Butterfly-Goddess-Slash-and-the-Berserk-White-TigerUTS, Chapter 51': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'The Unrivaled Tang Sect',
		'resolved_url': 'https://www.webnovel.com/book/8099443605005505/28376344349965359/The-Unrivaled-Tang-Sect/The-Butterfly-Goddess-Slash-and-the-Berserk-White-Tiger'
	},
	"https://www.webnovel.com/rssbook/8099443605005505/28427691489281729/The-Unrivaled-Tang-Sect/The-Ice-Empress'-ArmorUTS, Chapter 52": {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'The Unrivaled Tang Sect',
		'resolved_url': 'https://www.webnovel.com/book/8099443605005505/28427691489281729/The-Unrivaled-Tang-Sect/The-Ice-Empress&#39;-Armor'
	},
	'https://www.webnovel.com/rssbook/8099443605005505/28427747340635509/The-Unrivaled-Tang-Sect/-Irrefutable-Benefits?UTS, Chapter 53': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'The Unrivaled Tang Sect',
		'resolved_url': 'https://www.webnovel.com/book/8099443605005505/28427747340635509/The-Unrivaled-Tang-Sect/-Irrefutable-Benefits%3F'
	},
	"https://www.webnovel.com/rssbook/8099443605005505/28427849597765315/The-Unrivaled-Tang-Sect/Meeting-at-the-Sea-God's-PavilionUTS, Chapter 54": {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'The Unrivaled Tang Sect',
		'resolved_url': 'https://www.webnovel.com/book/8099443605005505/28427849597765315/The-Unrivaled-Tang-Sect/Meeting-at-the-Sea-God&#39;s-Pavilion'
	},
	"https://www.webnovel.com/rssbook/8099443605005505/28427881021492603/The-Unrivaled-Tang-Sect/A-Soul-Engineer!-Huo-Yuhao's-True-Strong-PointUTS, Chapter 55": {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'The Unrivaled Tang Sect',
		'resolved_url': 'https://www.webnovel.com/book/8099443605005505/28427881021492603/The-Unrivaled-Tang-Sect/A-Soul-Engineer!-Huo-Yuhao&#39;s-True-Strong-Point'
	},
	'https://www.webnovel.com/rssbook/8099443605005505/28427945177566588/The-Unrivaled-Tang-Sect/The-Treasure-Appreciation-AuctionUTS, Chapter 56': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'The Unrivaled Tang Sect',
		'resolved_url': 'https://www.webnovel.com/book/8099443605005505/28427945177566588/The-Unrivaled-Tang-Sect/The-Treasure-Appreciation-Auction'
	},
	'https://www.webnovel.com/rssbook/8099443605005505/28427966904059588/The-Unrivaled-Tang-Sect/The-Golden-Left-Arm-BoneUTS, Chapter 57': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'The Unrivaled Tang Sect',
		'resolved_url': 'https://www.webnovel.com/book/8099443605005505/28427966904059588/The-Unrivaled-Tang-Sect/The-Golden-Left-Arm-Bone'
	},
	'https://www.webnovel.com/rssbook/8099443605005505/28427993210734277/The-Unrivaled-Tang-Sect/The-Boundary-Between-Life-and-DeathUTS, Chapter 58': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'The Unrivaled Tang Sect',
		'resolved_url': 'https://www.webnovel.com/book/8099443605005505/28427993210734277/The-Unrivaled-Tang-Sect/The-Boundary-Between-Life-and-Death'
	},
	'https://www.webnovel.com/rssbook/8099443605005505/28428017906796230/The-Unrivaled-Tang-Sect/The-Berserk-Flamedevil-Ma-Xiaotao!UTS, Chapter 59': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'The Unrivaled Tang Sect',
		'resolved_url': 'https://www.webnovel.com/book/8099443605005505/28428017906796230/The-Unrivaled-Tang-Sect/The-Berserk-Flamedevil-Ma-Xiaotao!'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394870366247/Coiling-Dragon/The-Yulan-Empire’s-Special-EnvoyCD, Chapter 255': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394870366247/Coiling-Dragon/The-Yulan-Empire%E2%80%99s-Special-Envoy'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395142766621/Coiling-Dragon/Blessing,-CurseCD, Chapter 511': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395142766621/Coiling-Dragon/Blessing%2C-Curse'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395683602452/Coiling-Dragon/Magic-Compilation,-Fusion-Sovereign!CD, Chapter 767': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395683602452/Coiling-Dragon/Magic-Compilation%2C-Fusion-Sovereign!'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394870906917/Coiling-Dragon/DeliaCD, Chapter 256': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394870906917/Coiling-Dragon/Delia'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412267036/Coiling-Dragon/Violet-Light-Rising-to-the-HeavensCD, Chapter 512': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412267036/Coiling-Dragon/Violet-Light-Rising-to-the-Heavens'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395953217556/Coiling-Dragon/EntrustedCD, Chapter 768': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395953217556/Coiling-Dragon/Entrusted'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394870923301/Coiling-Dragon/Meeting-Ten-Years-LaterCD, Chapter 257': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394870923301/Coiling-Dragon/Meeting-Ten-Years-Later'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412283420/Coiling-Dragon/The-Strange-Fog-SeaCD, Chapter 513': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412283420/Coiling-Dragon/The-Strange-Fog-Sea'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395953233940/Coiling-Dragon/Dragonblood-ContinentCD, Chapter 769': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395953233940/Coiling-Dragon/Dragonblood-Continent'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394870874149/Coiling-Dragon/Delia’s-ProtectorCD, Chapter 258': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394870874149/Coiling-Dragon/Delia%E2%80%99s-Protector'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412299804/Coiling-Dragon/HighgodCD, Chapter 514': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412299804/Coiling-Dragon/Highgod'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395953184788/Coiling-Dragon/EntreatyCD, Chapter 770': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395953184788/Coiling-Dragon/Entreaty'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394870890533/Coiling-Dragon/The-Anticipation-of-the-CrowdCD, Chapter 259': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394870890533/Coiling-Dragon/The-Anticipation-of-the-Crowd'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412316188/Coiling-Dragon/Amethyst-BeastsCD, Chapter 515': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412316188/Coiling-Dragon/Amethyst-Beasts'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395953201172/Coiling-Dragon/The-Next-Five-Thousand-YearsCD, Chapter 771': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395953201172/Coiling-Dragon/The-Next-Five-Thousand-Years'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394870972453/Coiling-Dragon/DesperateCD, Chapter 260': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394870972453/Coiling-Dragon/Desperate'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412201500/Coiling-Dragon/The-Storm-CavesCD, Chapter 516': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412201500/Coiling-Dragon/The-Storm-Caves'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395953152020/Coiling-Dragon/Sword-IntentCD, Chapter 772': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395953152020/Coiling-Dragon/Sword-Intent'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394870988837/Coiling-Dragon/AstonishmentCD, Chapter 261': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394870988837/Coiling-Dragon/Astonishment'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412217884/Coiling-Dragon/The-RescueCD, Chapter 517': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412217884/Coiling-Dragon/The-Rescue'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395953168404/Coiling-Dragon/Hunt-and-Kill,-A-Storm-Brews!CD, Chapter 773': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395953168404/Coiling-Dragon/Hunt-and-Kill%2C-A-Storm-Brews!'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394870939685/Coiling-Dragon/Fame-Spreading-FarCD, Chapter 262': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394870939685/Coiling-Dragon/Fame-Spreading-Far'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412234268/Coiling-Dragon/Juvenile-BeastCD, Chapter 518': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412234268/Coiling-Dragon/Juvenile-Beast'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395953119252/Coiling-Dragon/The-First-Display-of-PowerCD, Chapter 774': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395953119252/Coiling-Dragon/The-First-Display-of-Power'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394870956069/Coiling-Dragon/Anarchic-Lands!CD, Chapter 263': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394870956069/Coiling-Dragon/Anarchic-Lands!'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412250652/Coiling-Dragon/Fleeing-For-Their-LivesCD, Chapter 519': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412250652/Coiling-Dragon/Fleeing-For-Their-Lives'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395953135636/Coiling-Dragon/PunishmentCD, Chapter 775': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395953135636/Coiling-Dragon/Punishment'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871037989/Coiling-Dragon/Reynolds’-CrisisCD, Chapter 264': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871037989/Coiling-Dragon/Reynolds%E2%80%99-Crisis'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412398108/Coiling-Dragon/Life-in-the-Amethyst-MountainsCD, Chapter 520': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412398108/Coiling-Dragon/Life-in-the-Amethyst-Mountains'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395953348628/Coiling-Dragon/The-Gathering-of-the-SovereignsCD, Chapter 776': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395953348628/Coiling-Dragon/The-Gathering-of-the-Sovereigns'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871054373/Coiling-Dragon/Grievous-News-on-the-Wedding-DayCD, Chapter 265': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871054373/Coiling-Dragon/Grievous-News-on-the-Wedding-Day'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412414492/Coiling-Dragon/Trapped-Five-Hundred-YearsCD, Chapter 521': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412414492/Coiling-Dragon/Trapped-Five-Hundred-Years'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395953365012/Coiling-Dragon/Covetous-IntentCD, Chapter 777': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395953365012/Coiling-Dragon/Covetous-Intent'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871005221/Coiling-Dragon/Is-it-True?CD, Chapter 266': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871005221/Coiling-Dragon/Is-it-True%3F'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412430876/Coiling-Dragon/108CD, Chapter 522': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412430876/Coiling-Dragon/108'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395953315860/Coiling-Dragon/The-VerdictCD, Chapter 778': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395953315860/Coiling-Dragon/The-Verdict'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871021605/Coiling-Dragon/Up-and-the-TruthCD, Chapter 267': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871021605/Coiling-Dragon/Up-and-the-Truth'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412447260/Coiling-Dragon/Black-StoneCD, Chapter 523': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412447260/Coiling-Dragon/Black-Stone'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395953332244/Coiling-Dragon/Tenfold-Victor’s-RewardCD, Chapter 779': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395953332244/Coiling-Dragon/Tenfold-Victor%E2%80%99s-Reward'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871103525/Coiling-Dragon/The-Secrets-of-the-Yulan-ContinentCD, Chapter 268': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871103525/Coiling-Dragon/The-Secrets-of-the-Yulan-Continent'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412332572/Coiling-Dragon/Ten-Years-of-HarvestingCD, Chapter 524': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412332572/Coiling-Dragon/Ten-Years-of-Harvesting'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395953283092/Coiling-Dragon/Divine-Beast,-Sable-LeviathanCD, Chapter 780': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395953283092/Coiling-Dragon/Divine-Beast%2C-Sable-Leviathan'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871119909/Coiling-Dragon/The-War-God’s-FavorCD, Chapter 269': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871119909/Coiling-Dragon/The-War-God%E2%80%99s-Favor'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412348956/Coiling-Dragon/SaturationCD, Chapter 525': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412348956/Coiling-Dragon/Saturation'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395953299476/Coiling-Dragon/Orloff’s-InvitationCD, Chapter 781': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395953299476/Coiling-Dragon/Orloff%E2%80%99s-Invitation'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871070757/Coiling-Dragon/The-Southeast-Administrative-ProvinceCD, Chapter 270': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871070757/Coiling-Dragon/The-Southeast-Administrative-Province'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412365340/Coiling-Dragon/Out-To-SeaCD, Chapter 526': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412365340/Coiling-Dragon/Out-To-Sea'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395953250324/Coiling-Dragon/Fight,-Kill!CD, Chapter 782': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395953250324/Coiling-Dragon/Fight%2C-Kill!'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871087141/Coiling-Dragon/The-CorpseCD, Chapter 271': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871087141/Coiling-Dragon/The-Corpse'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412381724/Coiling-Dragon/That-Powerful-ManCD, Chapter 527': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412381724/Coiling-Dragon/That-Powerful-Man'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395953266708/Coiling-Dragon/Outside-of-One’s-ExpectationsCD, Chapter 783': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395953266708/Coiling-Dragon/Outside-of-One%E2%80%99s-Expectations'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394870661159/Coiling-Dragon/EnslavedCD, Chapter 272': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394870661159/Coiling-Dragon/Enslaved'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412545564/Coiling-Dragon/Knifeblade-IslandCD, Chapter 528': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412545564/Coiling-Dragon/Knifeblade-Island'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395952971796/Coiling-Dragon/Trump-CardCD, Chapter 784': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395952971796/Coiling-Dragon/Trump-Card'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394870644775/Coiling-Dragon/CrueltyCD, Chapter 273': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394870644775/Coiling-Dragon/Cruelty'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412529180/Coiling-Dragon/Hidden-ExpertCD, Chapter 529': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412529180/Coiling-Dragon/Hidden-Expert'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395952955412/Coiling-Dragon/Winged-AngelCD, Chapter 785': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395952955412/Coiling-Dragon/Winged-Angel'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394870628391/Coiling-Dragon/The-OrderCD, Chapter 274': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394870628391/Coiling-Dragon/The-Order'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412578332/Coiling-Dragon/Blackstone-PrisonCD, Chapter 530': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412578332/Coiling-Dragon/Blackstone-Prison'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395952939028/Coiling-Dragon/Nine-RoundsCD, Chapter 786': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395952939028/Coiling-Dragon/Nine-Rounds'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394870612007/Coiling-Dragon/Establishing-a-Base-in-the-Anarchic-LandsCD, Chapter 275': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394870612007/Coiling-Dragon/Establishing-a-Base-in-the-Anarchic-Lands'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412561948/Coiling-Dragon/EmotionsCD, Chapter 531': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412561948/Coiling-Dragon/Emotions'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395952922644/Coiling-Dragon/Revisiting-the-Divine-Light-PlaneCD, Chapter 787': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395952922644/Coiling-Dragon/Revisiting-the-Divine-Light-Plane'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394870726695/Coiling-Dragon/AdministrationCD, Chapter 276': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394870726695/Coiling-Dragon/Administration'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412480028/Coiling-Dragon/GanmontinCD, Chapter 532': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412480028/Coiling-Dragon/Ganmontin'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395952906260/Coiling-Dragon/An-Extremely-High-Price!CD, Chapter 788': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395952906260/Coiling-Dragon/An-Extremely-High-Price!'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394870710311/Coiling-Dragon/The-Mysterious-Mountain-VillageCD, Chapter 277': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394870710311/Coiling-Dragon/The-Mysterious-Mountain-Village'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412463644/Coiling-Dragon/So-It-Was-HimCD, Chapter 533': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412463644/Coiling-Dragon/So-It-Was-Him'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395952889876/Coiling-Dragon/MemoriesCD, Chapter 789': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395952889876/Coiling-Dragon/Memories'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394870693927/Coiling-Dragon/Linley-and-OlivierCD, Chapter 278': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394870693927/Coiling-Dragon/Linley-and-Olivier'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412512796/Coiling-Dragon/A-Great-BattleCD, Chapter 534': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412512796/Coiling-Dragon/A-Great-Battle'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395952873492/Coiling-Dragon/Beginning-to-ActCD, Chapter 790': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395952873492/Coiling-Dragon/Beginning-to-Act'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394870677543/Coiling-Dragon/Delia-and-LinleyCD, Chapter 279': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394870677543/Coiling-Dragon/Delia-and-Linley'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412496412/Coiling-Dragon/UnbindableCD, Chapter 535': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412496412/Coiling-Dragon/Unbindable'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395952857108/Coiling-Dragon/WindhunterCD, Chapter 791': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395952857108/Coiling-Dragon/Windhunter'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394870792230/Coiling-Dragon/Two-LettersCD, Chapter 280': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394870792230/Coiling-Dragon/Two-Letters'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412676635/Coiling-Dragon/Drifting-For-Twenty-YearsCD, Chapter 536': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412676635/Coiling-Dragon/Drifting-For-Twenty-Years'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395953102868/Coiling-Dragon/Sovereign’s-EmissariesCD, Chapter 792': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395953102868/Coiling-Dragon/Sovereign%E2%80%99s-Emissaries'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394870775847/Coiling-Dragon/Expanding-PowerCD, Chapter 281': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394870775847/Coiling-Dragon/Expanding-Power'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412660251/Coiling-Dragon/Miluo-IslandCD, Chapter 537': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412660251/Coiling-Dragon/Miluo-Island'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395953086484/Coiling-Dragon/A-MeetingCD, Chapter 793': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395953086484/Coiling-Dragon/A-Meeting'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394870759463/Coiling-Dragon/War-MachineCD, Chapter 282': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394870759463/Coiling-Dragon/War-Machine'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412709403/Coiling-Dragon/Familiar-FaceCD, Chapter 538': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412709403/Coiling-Dragon/Familiar-Face'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395953070100/Coiling-Dragon/Gathering-PointCD, Chapter 794': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395953070100/Coiling-Dragon/Gathering-Point'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394870743079/Coiling-Dragon/Heading-OutCD, Chapter 283': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394870743079/Coiling-Dragon/Heading-Out'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412693019/Coiling-Dragon/A-ConfrontationCD, Chapter 539': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412693019/Coiling-Dragon/A-Confrontation'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395953053716/Coiling-Dragon/The-Bula-RaceCD, Chapter 795': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395953053716/Coiling-Dragon/The-Bula-Race'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394870857766/Coiling-Dragon/Third-Bro?CD, Chapter 284': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394870857766/Coiling-Dragon/Third-Bro%3F'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412611099/Coiling-Dragon/Colored-Miluo-InsigniaCD, Chapter 540': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412611099/Coiling-Dragon/Colored-Miluo-Insignia'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395953037332/Coiling-Dragon/SamsaraCD, Chapter 796': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395953037332/Coiling-Dragon/Samsara'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394870841382/Coiling-Dragon/DesriCD, Chapter 285': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394870841382/Coiling-Dragon/Desri'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412594715/Coiling-Dragon/War-God,-CesarCD, Chapter 541': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412594715/Coiling-Dragon/War-God%2C-Cesar'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395953020948/Coiling-Dragon/Thousand-YearsCD, Chapter 797': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395953020948/Coiling-Dragon/Thousand-Years'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394870824998/Coiling-Dragon/The-Terrifying-Power-of-Grand-Magus-SaintsCD, Chapter 286': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394870824998/Coiling-Dragon/The-Terrifying-Power-of-Grand-Magus-Saints'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412643867/Coiling-Dragon/With-Child?CD, Chapter 542': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412643867/Coiling-Dragon/With-Child%3F'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395953004564/Coiling-Dragon/The-Final-BattleCD, Chapter 798': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395953004564/Coiling-Dragon/The-Final-Battle'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394870808614/Coiling-Dragon/SparringCD, Chapter 287': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394870808614/Coiling-Dragon/Sparring'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412627483/Coiling-Dragon/I-Want-Him-Dead!CD, Chapter 543': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412627483/Coiling-Dragon/I-Want-Him-Dead!'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395952988180/Coiling-Dragon/CatchingCD, Chapter 799': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395952988180/Coiling-Dragon/Catching'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871398435/Coiling-Dragon/Forget-It!CD, Chapter 288': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871398435/Coiling-Dragon/Forget-It!'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395411775517/Coiling-Dragon/All-Who-Bar-My-Path-Shall-Die!CD, Chapter 544': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395411775517/Coiling-Dragon/All-Who-Bar-My-Path-Shall-Die!'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395952791572/Coiling-Dragon/Lies!CD, Chapter 800': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395952791572/Coiling-Dragon/Lies!'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871414819/Coiling-Dragon/The-Order-Comes-DownCD, Chapter 289': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871414819/Coiling-Dragon/The-Order-Comes-Down'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395411791901/Coiling-Dragon/Turning-the-World-Upside-DownCD, Chapter 545': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395411791901/Coiling-Dragon/Turning-the-World-Upside-Down'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395952807956/Coiling-Dragon/Linley’s-Fiery-RageCD, Chapter 801': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395952807956/Coiling-Dragon/Linley%E2%80%99s-Fiery-Rage'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871431203/Coiling-Dragon/A-Sudden-Change-of-EventsCD, Chapter 290': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871431203/Coiling-Dragon/A-Sudden-Change-of-Events'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395411742749/Coiling-Dragon/Life-and-Death,-Two-PathsCD, Chapter 546': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395411742749/Coiling-Dragon/Life-and-Death%2C-Two-Paths'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395952824340/Coiling-Dragon/A-Battle-of-Chief-SovereignsCD, Chapter 802': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395952824340/Coiling-Dragon/A-Battle-of-Chief-Sovereigns'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871447587/Coiling-Dragon/Linley’s-ReturnCD, Chapter 291': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871447587/Coiling-Dragon/Linley%E2%80%99s-Return'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395411759133/Coiling-Dragon/Robed-ElderCD, Chapter 547': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395411759133/Coiling-Dragon/Robed-Elder'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395952840724/Coiling-Dragon/Can-He-Actually-Be…?CD, Chapter 803': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395952840724/Coiling-Dragon/Can-He-Actually-Be%E2%80%A6%3F'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394346913803/Coiling-Dragon/A-Congregation-of-TalentsCD, Chapter 36': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394346913803/Coiling-Dragon/A-Congregation-of-Talents'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871463971/Coiling-Dragon/DownfallCD, Chapter 292': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871463971/Coiling-Dragon/Downfall'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395411709981/Coiling-Dragon/Scryer-RecordsCD, Chapter 548': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395411709981/Coiling-Dragon/Scryer-Records'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395952742420/Coiling-Dragon/Earth-Fire-Water-WindCD, Chapter 804': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395952742420/Coiling-Dragon/Earth-Fire-Water-Wind'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394346930187/Coiling-Dragon/The-Bros-of-Dorm-1987-(part-1)CD, Chapter 37': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394346930187/Coiling-Dragon/The-Bros-of-Dorm-1987-(part-1)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871480355/Coiling-Dragon/The-Fierce-Battle-Against-OsennoCD, Chapter 293': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871480355/Coiling-Dragon/The-Fierce-Battle-Against-Osenno'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395411726365/Coiling-Dragon/Secret-AreaCD, Chapter 549': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395411726365/Coiling-Dragon/Secret-Area'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395952758804/Coiling-Dragon/A-New-Name-(part-1)CD, Chapter 805': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395952758804/Coiling-Dragon/A-New-Name-(part-1)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394346881035/Coiling-Dragon/The-Bros-of-Dorm-1987-(part-2)CD, Chapter 38': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394346881035/Coiling-Dragon/The-Bros-of-Dorm-1987-(part-2)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871496739/Coiling-Dragon/BaruchCD, Chapter 294': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871496739/Coiling-Dragon/Baruch'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395411677213/Coiling-Dragon/The-SecretCD, Chapter 550': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395411677213/Coiling-Dragon/The-Secret'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395952775188/Coiling-Dragon/A-New-Name-(part-2)CD, Chapter 806': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395952775188/Coiling-Dragon/A-New-Name-(part-2)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394346897419/Coiling-Dragon/Style-MagicCD, Chapter 39': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394346897419/Coiling-Dragon/Style-Magic'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871513123/Coiling-Dragon/HomecomingCD, Chapter 295': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871513123/Coiling-Dragon/Homecoming'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395411693597/Coiling-Dragon/Unable-to-Leave!CD, Chapter 551': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395411693597/Coiling-Dragon/Unable-to-Leave!'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394346979339/Coiling-Dragon/A-Learning-Period-(part-1)CD, Chapter 40': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394346979339/Coiling-Dragon/A-Learning-Period-(part-1)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871529507/Coiling-Dragon/(title-hidden)CD, Chapter 296': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871529507/Coiling-Dragon/(title-hidden)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395411906588/Coiling-Dragon/SledgehammerCD, Chapter 552': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395411906588/Coiling-Dragon/Sledgehammer'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394346995723/Coiling-Dragon/A-Learning-Period-(part-2)CD, Chapter 41': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394346995723/Coiling-Dragon/A-Learning-Period-(part-2)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871545891/Coiling-Dragon/KingdomCD, Chapter 297': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871545891/Coiling-Dragon/Kingdom'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395411922972/Coiling-Dragon/Purgatory-CommanderCD, Chapter 553': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395411922972/Coiling-Dragon/Purgatory-Commander'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394346946571/Coiling-Dragon/Who-is-Number-One?-(part-1)CD, Chapter 42': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394346946571/Coiling-Dragon/Who-is-Number-One%3F-(part-1)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871562275/Coiling-Dragon/A-Procession-of-ArrivalsCD, Chapter 298': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871562275/Coiling-Dragon/A-Procession-of-Arrivals'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395411873821/Coiling-Dragon/The-Might-of-a-SovereignCD, Chapter 554': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395411873821/Coiling-Dragon/The-Might-of-a-Sovereign'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394346962955/Coiling-Dragon/Who-is-Number-One?-(part-2)CD, Chapter 43': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394346962955/Coiling-Dragon/Who-is-Number-One%3F-(part-2)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871578659/Coiling-Dragon/The-Laws-of-LightCD, Chapter 299': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871578659/Coiling-Dragon/The-Laws-of-Light'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395411890205/Coiling-Dragon/Training-SpeedCD, Chapter 555': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395411890205/Coiling-Dragon/Training-Speed'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347044875/Coiling-Dragon/The-Proulx-Gallery-(part-1)CD, Chapter 44': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347044875/Coiling-Dragon/The-Proulx-Gallery-(part-1)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871595043/Coiling-Dragon/The-Four-Sided-GatheringCD, Chapter 300': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871595043/Coiling-Dragon/The-Four-Sided-Gathering'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395411841053/Coiling-Dragon/Travelling-to-Indigo-PrefectureCD, Chapter 556': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395411841053/Coiling-Dragon/Travelling-to-Indigo-Prefecture'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347061259/Coiling-Dragon/The-Proulx-Gallery-(part-two)CD, Chapter 45': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347061259/Coiling-Dragon/The-Proulx-Gallery-(part-two)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871611427/Coiling-Dragon/The-WeddingCD, Chapter 301': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871611427/Coiling-Dragon/The-Wedding'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395411857437/Coiling-Dragon/Azure-Dragon-ClanCD, Chapter 557': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395411857437/Coiling-Dragon/Azure-Dragon-Clan'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347012107/Coiling-Dragon/A-Wonderful-SurpriseCD, Chapter 46': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347012107/Coiling-Dragon/A-Wonderful-Surprise'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871627811/Coiling-Dragon/That-NightCD, Chapter 302': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871627811/Coiling-Dragon/That-Night'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395411808285/Coiling-Dragon/Seize-ThemCD, Chapter 558': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395411808285/Coiling-Dragon/Seize-Them'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347028491/Coiling-Dragon/The-Straight-Chisel-SchoolCD, Chapter 47': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347028491/Coiling-Dragon/The-Straight-Chisel-School'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871644195/Coiling-Dragon/Twelve-Years-in-the-Blink-of-an-EyeCD, Chapter 303': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871644195/Coiling-Dragon/Twelve-Years-in-the-Blink-of-an-Eye'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395411824669/Coiling-Dragon/BaruchCD, Chapter 559': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395411824669/Coiling-Dragon/Baruch'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347126795/Coiling-Dragon/Six-YearsCD, Chapter 48': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347126795/Coiling-Dragon/Six-Years'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871152677/Coiling-Dragon/Blueheart-Grass,-Dragon’s-BloodCD, Chapter 304': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871152677/Coiling-Dragon/Blueheart-Grass%2C-Dragon%E2%80%99s-Blood'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412054044/Coiling-Dragon/The-Weakest,-Smallest-BranchCD, Chapter 560': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412054044/Coiling-Dragon/The-Weakest%2C-Smallest-Branch'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347110411/Coiling-Dragon/Stone-Sculpting-(part-1)CD, Chapter 49': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347110411/Coiling-Dragon/Stone-Sculpting-(part-1)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871136294/Coiling-Dragon/A-Heated-BattleCD, Chapter 305': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871136294/Coiling-Dragon/A-Heated-Battle'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412037660/Coiling-Dragon/The-Clan’s-CrisisCD, Chapter 561': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412037660/Coiling-Dragon/The-Clan%E2%80%99s-Crisis'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347094027/Coiling-Dragon/Stone-Sculpting-(part-2)CD, Chapter 50': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347094027/Coiling-Dragon/Stone-Sculpting-(part-2)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871185445/Coiling-Dragon/SubmissionCD, Chapter 306': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871185445/Coiling-Dragon/Submission'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412021276/Coiling-Dragon/The-Secrets-of-the-Ancestral-Baptism!CD, Chapter 562': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412021276/Coiling-Dragon/The-Secrets-of-the-Ancestral-Baptism!'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347077643/Coiling-Dragon/A-Night-at-the-Jade-Water-ParadiseCD, Chapter 51': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347077643/Coiling-Dragon/A-Night-at-the-Jade-Water-Paradise'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871169061/Coiling-Dragon/GloryCD, Chapter 307': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871169061/Coiling-Dragon/Glory'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412004892/Coiling-Dragon/Eighty-YearsCD, Chapter 563': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412004892/Coiling-Dragon/Eighty-Years'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347192331/Coiling-Dragon/The-Price-(part-1)CD, Chapter 52': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347192331/Coiling-Dragon/The-Price-(part-1)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871218213/Coiling-Dragon/DiscoveryCD, Chapter 308': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871218213/Coiling-Dragon/Discovery'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395411988508/Coiling-Dragon/Dragonize-PoolCD, Chapter 564': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395411988508/Coiling-Dragon/Dragonize-Pool'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347175947/Coiling-Dragon/The-Price-(part-2)CD, Chapter 53': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347175947/Coiling-Dragon/The-Price-(part-2)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871201829/Coiling-Dragon/Magicite-Gemstone-MineCD, Chapter 309': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871201829/Coiling-Dragon/Magicite-Gemstone-Mine'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395411972124/Coiling-Dragon/Innate-Divine-AbilityCD, Chapter 565': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395411972124/Coiling-Dragon/Innate-Divine-Ability'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347159563/Coiling-Dragon/The-InvitationCD, Chapter 54': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347159563/Coiling-Dragon/The-Invitation'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871250981/Coiling-Dragon/Joining-ForcesCD, Chapter 310': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871250981/Coiling-Dragon/Joining-Forces'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395411955740/Coiling-Dragon/The-Might-of-the-Dragon-RoarCD, Chapter 566': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395411955740/Coiling-Dragon/The-Might-of-the-Dragon-Roar'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347143179/Coiling-Dragon/The-Journey-(part-1)CD, Chapter 55': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347143179/Coiling-Dragon/The-Journey-(part-1)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871234597/Coiling-Dragon/Calling-the-Troops,-Summoning-the-GeneralsCD, Chapter 311': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871234597/Coiling-Dragon/Calling-the-Troops%2C-Summoning-the-Generals'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395411939356/Coiling-Dragon/Greed!CD, Chapter 567': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395411939356/Coiling-Dragon/Greed!'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347257867/Coiling-Dragon/The-Journey-(part-2)CD, Chapter 56': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347257867/Coiling-Dragon/The-Journey-(part-2)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871283748/Coiling-Dragon/A-Beast-of-Burden?CD, Chapter 312': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871283748/Coiling-Dragon/A-Beast-of-Burden%3F'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412185116/Coiling-Dragon/The-ChallengeCD, Chapter 568': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412185116/Coiling-Dragon/The-Challenge'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347241483/Coiling-Dragon/The-Mountain-Range-of-Magical-Beasts-(part-1)CD, Chapter 57': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347241483/Coiling-Dragon/The-Mountain-Range-of-Magical-Beasts-(part-1)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871267365/Coiling-Dragon/The-Call-to-AssembleCD, Chapter 313': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871267365/Coiling-Dragon/The-Call-to-Assemble'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412168732/Coiling-Dragon/And,-Death-DuelCD, Chapter 569': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412168732/Coiling-Dragon/And%2C-Death-Duel'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347225099/Coiling-Dragon/The-Mountain-Range-of-Magical-Beasts-(part-2)CD, Chapter 58': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347225099/Coiling-Dragon/The-Mountain-Range-of-Magical-Beasts-(part-2)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871316515/Coiling-Dragon/The-DoorCD, Chapter 314': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871316515/Coiling-Dragon/The-Door'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412152348/Coiling-Dragon/No-Mercy!CD, Chapter 570': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412152348/Coiling-Dragon/No-Mercy!'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347208715/Coiling-Dragon/Wolf-Pack-(part-1)CD, Chapter 59': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347208715/Coiling-Dragon/Wolf-Pack-(part-1)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871300131/Coiling-Dragon/The-Power-of-Magicite-CannonsCD, Chapter 315': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871300131/Coiling-Dragon/The-Power-of-Magicite-Cannons'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412135964/Coiling-Dragon/PrestigeCD, Chapter 571': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412135964/Coiling-Dragon/Prestige'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347323403/Coiling-Dragon/Wolf-Pack-(part-2)CD, Chapter 60': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347323403/Coiling-Dragon/Wolf-Pack-(part-2)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871349283/Coiling-Dragon/Explosive-FuryCD, Chapter 316': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871349283/Coiling-Dragon/Explosive-Fury'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412119580/Coiling-Dragon/‘Punishment’CD, Chapter 572': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412119580/Coiling-Dragon/%E2%80%98Punishment%E2%80%99'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347307019/Coiling-Dragon/Danger-(part-1)CD, Chapter 61': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347307019/Coiling-Dragon/Danger-(part-1)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871332899/Coiling-Dragon/Battle-to-the-DeathCD, Chapter 317': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871332899/Coiling-Dragon/Battle-to-the-Death'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412103196/Coiling-Dragon/ElderCD, Chapter 573': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412103196/Coiling-Dragon/Elder'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347290635/Coiling-Dragon/Danger-(part-2)CD, Chapter 62': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347290635/Coiling-Dragon/Danger-(part-2)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871382051/Coiling-Dragon/Meat-GrinderCD, Chapter 318': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871382051/Coiling-Dragon/Meat-Grinder'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412086812/Coiling-Dragon/Conclave-of-EldersCD, Chapter 574': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412086812/Coiling-Dragon/Conclave-of-Elders'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347274251/Coiling-Dragon/CrueltyCD, Chapter 63': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347274251/Coiling-Dragon/Cruelty'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871365667/Coiling-Dragon/Trump-CardCD, Chapter 319': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871365667/Coiling-Dragon/Trump-Card'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412070428/Coiling-Dragon/The-Grand-ElderCD, Chapter 575': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412070428/Coiling-Dragon/The-Grand-Elder'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347405323/Coiling-Dragon/Cruelty-(part-2)CD, Chapter 64': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347405323/Coiling-Dragon/Cruelty-(part-2)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394872021027/Coiling-Dragon/An-Utter-CatastropheCD, Chapter 320': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394872021027/Coiling-Dragon/An-Utter-Catastrophe'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395413250074/Coiling-Dragon/ComfortCD, Chapter 576': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395413250074/Coiling-Dragon/Comfort'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347421707/Coiling-Dragon/Bebe’s-Prowess-(part-1)CD, Chapter 65': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347421707/Coiling-Dragon/Bebe%E2%80%99s-Prowess-(part-1)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394872037411/Coiling-Dragon/The-Ratmageddon-WaveCD, Chapter 321': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394872037411/Coiling-Dragon/The-Ratmageddon-Wave'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395413266458/Coiling-Dragon/Receiving-the-OrderCD, Chapter 577': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395413266458/Coiling-Dragon/Receiving-the-Order'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347438091/Coiling-Dragon/Bebe’s-Prowess-(part-2)CD, Chapter 66': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347438091/Coiling-Dragon/Bebe%E2%80%99s-Prowess-(part-2)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871988259/Coiling-Dragon/Meeting-InvitationCD, Chapter 322': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871988259/Coiling-Dragon/Meeting-Invitation'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395413282842/Coiling-Dragon/Give-Me-a-RideCD, Chapter 578': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395413282842/Coiling-Dragon/Give-Me-a-Ride'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347454475/Coiling-Dragon/The-Black-Dagger-(part-1)CD, Chapter 67': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347454475/Coiling-Dragon/The-Black-Dagger-(part-1)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394872004643/Coiling-Dragon/ShamelessCD, Chapter 323': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394872004643/Coiling-Dragon/Shameless'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395413299226/Coiling-Dragon/Blood-Splattering-the-SkiesCD, Chapter 579': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395413299226/Coiling-Dragon/Blood-Splattering-the-Skies'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347339787/Coiling-Dragon/The-Black-Dagger-(part-2)CD, Chapter 68': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347339787/Coiling-Dragon/The-Black-Dagger-(part-2)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871955491/Coiling-Dragon/A-Falling-OutCD, Chapter 324': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871955491/Coiling-Dragon/A-Falling-Out'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395413315610/Coiling-Dragon/Spiritual-ChaosCD, Chapter 580': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395413315610/Coiling-Dragon/Spiritual-Chaos'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347356171/Coiling-Dragon/The-Foggy-Gulch-(part-1)CD, Chapter 69': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347356171/Coiling-Dragon/The-Foggy-Gulch-(part-1)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871971875/Coiling-Dragon/Downfall-of-Many-SaintsCD, Chapter 325': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871971875/Coiling-Dragon/Downfall-of-Many-Saints'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395413331994/Coiling-Dragon/BestowalCD, Chapter 581': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395413331994/Coiling-Dragon/Bestowal'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347372555/Coiling-Dragon/The-Foggy-Gulch-(part-2)CD, Chapter 70': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347372555/Coiling-Dragon/The-Foggy-Gulch-(part-2)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871922723/Coiling-Dragon/BeirutCD, Chapter 326': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871922723/Coiling-Dragon/Beirut'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395413348378/Coiling-Dragon/FreedomCD, Chapter 582': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395413348378/Coiling-Dragon/Freedom'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347388939/Coiling-Dragon/Her-Name-Was-Alice(part-1)CD, Chapter 71': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347388939/Coiling-Dragon/Her-Name-Was-Alice(part-1)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871939107/Coiling-Dragon/Founding-of-an-EmpireCD, Chapter 327': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871939107/Coiling-Dragon/Founding-of-an-Empire'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395413364762/Coiling-Dragon/Joining-ForcesCD, Chapter 583': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395413364762/Coiling-Dragon/Joining-Forces'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347536395/Coiling-Dragon/Her-Name-Was-Alice(part-2)CD, Chapter 72': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347536395/Coiling-Dragon/Her-Name-Was-Alice(part-2)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394872152099/Coiling-Dragon/BreakthroughCD, Chapter 328': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394872152099/Coiling-Dragon/Breakthrough'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395413381146/Coiling-Dragon/Surrounded-And-AttackedCD, Chapter 584': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395413381146/Coiling-Dragon/Surrounded-And-Attacked'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347552779/Coiling-Dragon/Violet-in-the-Night-Wind-(part-1)CD, Chapter 73': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347552779/Coiling-Dragon/Violet-in-the-Night-Wind-(part-1)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394872168483/Coiling-Dragon/Bebe’s-HeritageCD, Chapter 329': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394872168483/Coiling-Dragon/Bebe%E2%80%99s-Heritage'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395413397530/Coiling-Dragon/A-Battle-of-Sovereign’s-MightsCD, Chapter 585': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395413397530/Coiling-Dragon/A-Battle-of-Sovereign%E2%80%99s-Mights'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347569163/Coiling-Dragon/Violet-in-the-Night-Wind-(part-2)CD, Chapter 74': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347569163/Coiling-Dragon/Violet-in-the-Night-Wind-(part-2)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394872119331/Coiling-Dragon/Deity-Level-Magical-BeastCD, Chapter 330': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394872119331/Coiling-Dragon/Deity-Level-Magical-Beast'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395413413914/Coiling-Dragon/Wanting-to-Steal-a-Chicken,-Instead-Losing-the-BaitCD, Chapter 586': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395413413914/Coiling-Dragon/Wanting-to-Steal-a-Chicken%2C-Instead-Losing-the-Bait'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347585547/Coiling-Dragon/Coming-Home-(part-1)CD, Chapter 75': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347585547/Coiling-Dragon/Coming-Home-(part-1)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394872135715/Coiling-Dragon/Bebe’s-RevengeCD, Chapter 331': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394872135715/Coiling-Dragon/Bebe%E2%80%99s-Revenge'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395413430298/Coiling-Dragon/Bulo,-Unwilling-to-Give-UpCD, Chapter 587': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395413430298/Coiling-Dragon/Bulo%2C-Unwilling-to-Give-Up'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347470859/Coiling-Dragon/Coming-Home-(part-2)CD, Chapter 76': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347470859/Coiling-Dragon/Coming-Home-(part-2)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394872086563/Coiling-Dragon/Everyone-AssembledCD, Chapter 332': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394872086563/Coiling-Dragon/Everyone-Assembled'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395413446682/Coiling-Dragon/The-Eight-Great-PatriarchsCD, Chapter 588': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395413446682/Coiling-Dragon/The-Eight-Great-Patriarchs'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347487243/Coiling-Dragon/HoggCD, Chapter 77': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347487243/Coiling-Dragon/Hogg'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394872102947/Coiling-Dragon/The-Metallic-CastleCD, Chapter 333': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394872102947/Coiling-Dragon/The-Metallic-Castle'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395413463066/Coiling-Dragon/A-Tremendous-Threat!CD, Chapter 589': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395413463066/Coiling-Dragon/A-Tremendous-Threat!'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347503627/Coiling-Dragon/The-Price-of-a-SculptureCD, Chapter 78': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347503627/Coiling-Dragon/The-Price-of-a-Sculpture'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394872053795/Coiling-Dragon/Three-CorridorsCD, Chapter 334': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394872053795/Coiling-Dragon/Three-Corridors'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395413479450/Coiling-Dragon/DecisionCD, Chapter 590': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395413479450/Coiling-Dragon/Decision'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347520011/Coiling-Dragon/The-Rose-in-Winter-(part-1)CD, Chapter 79': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347520011/Coiling-Dragon/The-Rose-in-Winter-(part-1)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394872070179/Coiling-Dragon/The-Necropolis’-SculpturesCD, Chapter 335': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394872070179/Coiling-Dragon/The-Necropolis%E2%80%99-Sculptures'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395681931290/Coiling-Dragon/Calmness-and-SavageryCD, Chapter 591': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395681931290/Coiling-Dragon/Calmness-and-Savagery'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394616119306/Coiling-Dragon/The-Rose-in-Winter-(part-2)CD, Chapter 80': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394616119306/Coiling-Dragon/The-Rose-in-Winter-(part-2)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871775267/Coiling-Dragon/Moving-CautiouslyCD, Chapter 336': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871775267/Coiling-Dragon/Moving-Cautiously'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395681964058/Coiling-Dragon/Most-Powerful-AttackCD, Chapter 592': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395681964058/Coiling-Dragon/Most-Powerful-Attack'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394616102922/Coiling-Dragon/Experts-Everywhere-(part-1)CD, Chapter 81': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394616102922/Coiling-Dragon/Experts-Everywhere-(part-1)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871758883/Coiling-Dragon/Plant-LifeformsCD, Chapter 337': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871758883/Coiling-Dragon/Plant-Lifeforms'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395681947674/Coiling-Dragon/Firmament-SplitterCD, Chapter 593': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395681947674/Coiling-Dragon/Firmament-Splitter'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394616152074/Coiling-Dragon/Experts-Everywhere-(part-2)CD, Chapter 82': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394616152074/Coiling-Dragon/Experts-Everywhere-(part-2)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871742499/Coiling-Dragon/The-Ba-Serpent-Awakens?CD, Chapter 338': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871742499/Coiling-Dragon/The-Ba-Serpent-Awakens%3F'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395681996825/Coiling-Dragon/BetrayalCD, Chapter 594': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395681996825/Coiling-Dragon/Betrayal'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394616135690/Coiling-Dragon/Cracks-(part-1)CD, Chapter 83': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394616135690/Coiling-Dragon/Cracks-(part-1)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871726115/Coiling-Dragon/True-Awakening!-The-Impending-Calamity!CD, Chapter 339': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871726115/Coiling-Dragon/True-Awakening!-The-Impending-Calamity!'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395681980442/Coiling-Dragon/A-MysteriousVisitorCD, Chapter 595': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395681980442/Coiling-Dragon/A-MysteriousVisitor'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347618314/Coiling-Dragon/Cracks-(part-2)CD, Chapter 84': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347618314/Coiling-Dragon/Cracks-(part-2)'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871709731/Coiling-Dragon/The-World-of-SnowCD, Chapter 340': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871709731/Coiling-Dragon/The-World-of-Snow'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395682029593/Coiling-Dragon/Nobody-ThereCD, Chapter 596': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395682029593/Coiling-Dragon/Nobody-There'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347601930/Coiling-Dragon/A-MeetingCD, Chapter 85': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347601930/Coiling-Dragon/A-Meeting'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871693347/Coiling-Dragon/Eight-Years-in-the-NecropolisCD, Chapter 341': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871693347/Coiling-Dragon/Eight-Years-in-the-Necropolis'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395682013209/Coiling-Dragon/WadeCD, Chapter 597': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395682013209/Coiling-Dragon/Wade'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394616086538/Coiling-Dragon/The-Desolate-SnowCD, Chapter 86': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394616086538/Coiling-Dragon/The-Desolate-Snow'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871676963/Coiling-Dragon/The-Flame-TyrantCD, Chapter 342': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871676963/Coiling-Dragon/The-Flame-Tyrant'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395682062361/Coiling-Dragon/Catching-a-RideCD, Chapter 598': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395682062361/Coiling-Dragon/Catching-a-Ride'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394347634698/Coiling-Dragon/Ten-Days,-Ten-NightsCD, Chapter 87': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394347634698/Coiling-Dragon/Ten-Days%2C-Ten-Nights'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871660579/Coiling-Dragon/The-Tunnel’s-LocationCD, Chapter 343': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871660579/Coiling-Dragon/The-Tunnel%E2%80%99s-Location'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395682045977/Coiling-Dragon/A-Frantic-BattleCD, Chapter 599': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395682045977/Coiling-Dragon/A-Frantic-Battle'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394616250378/Coiling-Dragon/LiquefyCD, Chapter 88': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394616250378/Coiling-Dragon/Liquefy'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871906339/Coiling-Dragon/The-Fate-Determining-StrikeCD, Chapter 344': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871906339/Coiling-Dragon/The-Fate-Determining-Strike'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395682095129/Coiling-Dragon/Spare-No-One!CD, Chapter 600': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395682095129/Coiling-Dragon/Spare-No-One!'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394616233994/Coiling-Dragon/Returning-to-the-Foggy-ValleyCD, Chapter 89': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394616233994/Coiling-Dragon/Returning-to-the-Foggy-Valley'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871889955/Coiling-Dragon/Three-Divine-ArtifactsCD, Chapter 345': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871889955/Coiling-Dragon/Three-Divine-Artifacts'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395682078745/Coiling-Dragon/Begging-for-SalvationCD, Chapter 601': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395682078745/Coiling-Dragon/Begging-for-Salvation'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394616283146/Coiling-Dragon/Forbidden-the-SkiesCD, Chapter 90': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394616283146/Coiling-Dragon/Forbidden-the-Skies'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871873571/Coiling-Dragon/The-Magical-Beasts-in-ActionCD, Chapter 346': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871873571/Coiling-Dragon/The-Magical-Beasts-in-Action'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395682127897/Coiling-Dragon/Their-ProposalsCD, Chapter 602': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395682127897/Coiling-Dragon/Their-Proposals'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394616266762/Coiling-Dragon/The-Gloomy-DepthsCD, Chapter 91': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394616266762/Coiling-Dragon/The-Gloomy-Depths'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871857187/Coiling-Dragon/The-Queen-Mother,-‘Lachapalle’CD, Chapter 347': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871857187/Coiling-Dragon/The-Queen-Mother%2C-%E2%80%98Lachapalle%E2%80%99'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395682111513/Coiling-Dragon/Three-MonthsCD, Chapter 603': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395682111513/Coiling-Dragon/Three-Months'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394616184842/Coiling-Dragon/The-Armored-Razorback-WyrmCD, Chapter 92': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394616184842/Coiling-Dragon/The-Armored-Razorback-Wyrm'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871840803/Coiling-Dragon/RegrowthCD, Chapter 348': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871840803/Coiling-Dragon/Regrowth'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395682160665/Coiling-Dragon/Between-Life-and-Death!CD, Chapter 604': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395682160665/Coiling-Dragon/Between-Life-and-Death!'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394616168458/Coiling-Dragon/ViciousnessCD, Chapter 93': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394616168458/Coiling-Dragon/Viciousness'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871824419/Coiling-Dragon/Fast,-Slow?CD, Chapter 349': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871824419/Coiling-Dragon/Fast%2C-Slow%3F'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395682144281/Coiling-Dragon/Beirut’s-AbilitiesCD, Chapter 605': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395682144281/Coiling-Dragon/Beirut%E2%80%99s-Abilities'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394616217610/Coiling-Dragon/The-Draconic-Crystal’s-TransformationCD, Chapter 94': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394616217610/Coiling-Dragon/The-Draconic-Crystal%E2%80%99s-Transformation'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871808035/Coiling-Dragon/Myriad-Swords-Converge,-the-Pearl-of-Life!CD, Chapter 350': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871808035/Coiling-Dragon/Myriad-Swords-Converge%2C-the-Pearl-of-Life!'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395682193433/Coiling-Dragon/Two-Drops-of-Sovereign’s-MightCD, Chapter 606': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395682193433/Coiling-Dragon/Two-Drops-of-Sovereign%E2%80%99s-Might'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394616201226/Coiling-Dragon/The-Dragonblood-WarriorCD, Chapter 95': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394616201226/Coiling-Dragon/The-Dragonblood-Warrior'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394871791651/Coiling-Dragon/Entering-the-Eighth-FloorCD, Chapter 351': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394871791651/Coiling-Dragon/Entering-the-Eighth-Floor'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395682177049/Coiling-Dragon/Putting-on-a-PerformanceCD, Chapter 607': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395682177049/Coiling-Dragon/Putting-on-a-Performance'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394599653452/Coiling-Dragon/The-Mysterious-Magical-FormationCD, Chapter 96': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394599653452/Coiling-Dragon/The-Mysterious-Magical-Formation'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395140948001/Coiling-Dragon/The-Beholder-KingCD, Chapter 352': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395140948001/Coiling-Dragon/The-Beholder-King'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412758555/Coiling-Dragon/Nowhere-to-RunCD, Chapter 608': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412758555/Coiling-Dragon/Nowhere-to-Run'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394599669831/Coiling-Dragon/The-Four-Higher-PlanesCD, Chapter 97': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394599669831/Coiling-Dragon/The-Four-Higher-Planes'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395140964385/Coiling-Dragon/A-Hospitable-HostCD, Chapter 353': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395140964385/Coiling-Dragon/A-Hospitable-Host'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412774939/Coiling-Dragon/Beirut’s-CraftinessCD, Chapter 609': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412774939/Coiling-Dragon/Beirut%E2%80%99s-Craftiness'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394599630811/Coiling-Dragon/Piercing-the-HeavensCD, Chapter 98': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394599630811/Coiling-Dragon/Piercing-the-Heavens'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395140980769/Coiling-Dragon/Thorium-DevilCD, Chapter 354': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395140980769/Coiling-Dragon/Thorium-Devil'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412725787/Coiling-Dragon/VitalityCD, Chapter 610': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412725787/Coiling-Dragon/Vitality'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394599637070/Coiling-Dragon/Grandmaster-Sculptor?CD, Chapter 99': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394599637070/Coiling-Dragon/Grandmaster-Sculptor%3F'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395140997153/Coiling-Dragon/Abyssal-Blade-DemonCD, Chapter 355': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395140997153/Coiling-Dragon/Abyssal-Blade-Demon'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412742171/Coiling-Dragon/DangerousCD, Chapter 611': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412742171/Coiling-Dragon/Dangerous'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394599595453/Coiling-Dragon/Sword-TrainingCD, Chapter 100': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394599595453/Coiling-Dragon/Sword-Training'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395140882466/Coiling-Dragon/Grand-Magus-SaintCD, Chapter 356': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395140882466/Coiling-Dragon/Grand-Magus-Saint'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412824091/Coiling-Dragon/UnwillingnessCD, Chapter 612': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412824091/Coiling-Dragon/Unwillingness'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394599602809/Coiling-Dragon/Applying-For-GraduationCD, Chapter 101': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394599602809/Coiling-Dragon/Applying-For-Graduation'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395140898849/Coiling-Dragon/Necropolis-of-the-Gods,-the-Eleventh-Floor!CD, Chapter 357': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395140898849/Coiling-Dragon/Necropolis-of-the-Gods%2C-the-Eleventh-Floor!'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412840475/Coiling-Dragon/SuspicionCD, Chapter 613': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412840475/Coiling-Dragon/Suspicion'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394616303636/Coiling-Dragon/Second-in-HistoryCD, Chapter 102': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394616303636/Coiling-Dragon/Second-in-History'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395140915233/Coiling-Dragon/The-Blood-Stained-UndergroundCD, Chapter 358': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395140915233/Coiling-Dragon/The-Blood-Stained-Underground'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412791323/Coiling-Dragon/A-Major-EventCD, Chapter 614': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412791323/Coiling-Dragon/A-Major-Event'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394616303637/Coiling-Dragon/The-Upper-Classes-of-the-Yulan-ContinentCD, Chapter 103': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394616303637/Coiling-Dragon/The-Upper-Classes-of-the-Yulan-Continent'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395140931617/Coiling-Dragon/Life-and-DeathCD, Chapter 359': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395140931617/Coiling-Dragon/Life-and-Death'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412807707/Coiling-Dragon/Group-BattleCD, Chapter 615': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412807707/Coiling-Dragon/Group-Battle'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394599784507/Coiling-Dragon/AbductionCD, Chapter 104': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394599784507/Coiling-Dragon/Abduction'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395141079073/Coiling-Dragon/Death?CD, Chapter 360': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395141079073/Coiling-Dragon/Death%3F'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412889627/Coiling-Dragon/The-Thorn-in-Their-SideCD, Chapter 616': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412889627/Coiling-Dragon/The-Thorn-in-Their-Side'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394599800890/Coiling-Dragon/StatusCD, Chapter 105': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394599800890/Coiling-Dragon/Status'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395141095457/Coiling-Dragon/Fleeing-For-His-LifeCD, Chapter 361': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395141095457/Coiling-Dragon/Fleeing-For-His-Life'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412906011/Coiling-Dragon/A-Turn-Of-EventsCD, Chapter 617': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412906011/Coiling-Dragon/A-Turn-Of-Events'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394599751741/Coiling-Dragon/A-Lack-of-MoneyCD, Chapter 106': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394599751741/Coiling-Dragon/A-Lack-of-Money'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395141111841/Coiling-Dragon/One-Against-a-MillionCD, Chapter 362': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395141111841/Coiling-Dragon/One-Against-a-Million'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412856859/Coiling-Dragon/SupremacyCD, Chapter 618': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412856859/Coiling-Dragon/Supremacy'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394599768124/Coiling-Dragon/RageCD, Chapter 107': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394599768124/Coiling-Dragon/Rage'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395141128225/Coiling-Dragon/Divine-SparkCD, Chapter 363': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395141128225/Coiling-Dragon/Divine-Spark'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412873243/Coiling-Dragon/What-Type-of-Weapon?CD, Chapter 619': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412873243/Coiling-Dragon/What-Type-of-Weapon%3F'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394599718975/Coiling-Dragon/The-Old-MasterCD, Chapter 108': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394599718975/Coiling-Dragon/The-Old-Master'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395141013537/Coiling-Dragon/Desiring-a-Divine-Spark?CD, Chapter 364': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395141013537/Coiling-Dragon/Desiring-a-Divine-Spark%3F'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412955162/Coiling-Dragon/MirageCD, Chapter 620': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412955162/Coiling-Dragon/Mirage'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394599735359/Coiling-Dragon/The-AuctionCD, Chapter 109': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394599735359/Coiling-Dragon/The-Auction'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395141029921/Coiling-Dragon/The-Predictions-of-BeirutCD, Chapter 365': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395141029921/Coiling-Dragon/The-Predictions-of-Beirut'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412971546/Coiling-Dragon/GoalsCD, Chapter 621': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412971546/Coiling-Dragon/Goals'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394599686212/Coiling-Dragon/High-PriceCD, Chapter 110': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394599686212/Coiling-Dragon/High-Price'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395141046305/Coiling-Dragon/Coming-HomeCD, Chapter 366': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395141046305/Coiling-Dragon/Coming-Home'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412922394/Coiling-Dragon/Ironknife-GorgeCD, Chapter 622': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412922394/Coiling-Dragon/Ironknife-Gorge'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394599714287/Coiling-Dragon/An-Owner-FoundCD, Chapter 111': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394599714287/Coiling-Dragon/An-Owner-Found'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395141062689/Coiling-Dragon/Becoming-a-Deity?CD, Chapter 367': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395141062689/Coiling-Dragon/Becoming-a-Deity%3F'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412938778/Coiling-Dragon/Back-to-the-Yulan-Continent!CD, Chapter 623': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412938778/Coiling-Dragon/Back-to-the-Yulan-Continent!'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394599931957/Coiling-Dragon/Going-HomeCD, Chapter 112': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394599931957/Coiling-Dragon/Going-Home'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394872266787/Coiling-Dragon/Dividing-the-TreasuresCD, Chapter 368': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394872266787/Coiling-Dragon/Dividing-the-Treasures'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395413037082/Coiling-Dragon/After-Two-Thousand-Years,-Even-Seas-Can-Become-Plains!CD, Chapter 624': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395413037082/Coiling-Dragon/After-Two-Thousand-Years%2C-Even-Seas-Can-Become-Plains!'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394599915573/Coiling-Dragon/The-Dusty-Affairs-of-the-PastCD, Chapter 113': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394599915573/Coiling-Dragon/The-Dusty-Affairs-of-the-Past'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394872250403/Coiling-Dragon/A-Major-EventCD, Chapter 369': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394872250403/Coiling-Dragon/A-Major-Event'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395413020698/Coiling-Dragon/Parting-WordsCD, Chapter 625': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395413020698/Coiling-Dragon/Parting-Words'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394599899190/Coiling-Dragon/The-DecisionCD, Chapter 114': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394599899190/Coiling-Dragon/The-Decision'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395140735011/Coiling-Dragon/The-Apocalypse-War-of-Ten-Thousand-Years-AgoCD, Chapter 370': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395140735011/Coiling-Dragon/The-Apocalypse-War-of-Ten-Thousand-Years-Ago'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395413004314/Coiling-Dragon/Marvelous-TreasuresCD, Chapter 626': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395413004314/Coiling-Dragon/Marvelous-Treasures'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394599882806/Coiling-Dragon/Assembling-at-the-TownshipCD, Chapter 115': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394599882806/Coiling-Dragon/Assembling-at-the-Township'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395140718627/Coiling-Dragon/Slaughtering-a-Path-to-the-Sacred-IsleCD, Chapter 371': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395140718627/Coiling-Dragon/Slaughtering-a-Path-to-the-Sacred-Isle'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395412987930/Coiling-Dragon/Battle!CD, Chapter 627': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395412987930/Coiling-Dragon/Battle!'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394599866422/Coiling-Dragon/A-Nighttime-ChatCD, Chapter 116': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394599866422/Coiling-Dragon/A-Nighttime-Chat'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394872201251/Coiling-Dragon/Judgment-Day-DescendsCD, Chapter 372': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394872201251/Coiling-Dragon/Judgment-Day-Descends'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395413102618/Coiling-Dragon/The-Manner-of-DeathCD, Chapter 628': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395413102618/Coiling-Dragon/The-Manner-of-Death'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394599850038/Coiling-Dragon/Writ-of-NobilityCD, Chapter 117': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394599850038/Coiling-Dragon/Writ-of-Nobility'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394872184867/Coiling-Dragon/Point-Battle-FormationCD, Chapter 373': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394872184867/Coiling-Dragon/Point-Battle-Formation'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395413086234/Coiling-Dragon/A-Pleasant-SurpriseCD, Chapter 629': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395413086234/Coiling-Dragon/A-Pleasant-Surprise'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394599833656/Coiling-Dragon/Tomes-of-MagicCD, Chapter 118': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394599833656/Coiling-Dragon/Tomes-of-Magic'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394872234019/Coiling-Dragon/The-DescentCD, Chapter 374': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394872234019/Coiling-Dragon/The-Descent'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395413069850/Coiling-Dragon/Entering-the-NetherworldCD, Chapter 630': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395413069850/Coiling-Dragon/Entering-the-Netherworld'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394599817273/Coiling-Dragon/Heavy-CasualtiesCD, Chapter 119': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394599817273/Coiling-Dragon/Heavy-Casualties'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394872217635/Coiling-Dragon/Lord-Chiquitas!CD, Chapter 375': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394872217635/Coiling-Dragon/Lord-Chiquitas!'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395413053466/Coiling-Dragon/Northbone-PrefectureCD, Chapter 631': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395413053466/Coiling-Dragon/Northbone-Prefecture'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394600063027/Coiling-Dragon/An-Excessive-Desire-to-KillCD, Chapter 120': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394600063027/Coiling-Dragon/An-Excessive-Desire-to-Kill'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395140833314/Coiling-Dragon/One-NightCD, Chapter 376': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395140833314/Coiling-Dragon/One-Night'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395413168154/Coiling-Dragon/SayantCD, Chapter 632': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395413168154/Coiling-Dragon/Sayant'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394600046643/Coiling-Dragon/The-EngagementCD, Chapter 121': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394600046643/Coiling-Dragon/The-Engagement'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395140816930/Coiling-Dragon/New-VariablesCD, Chapter 377': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395140816930/Coiling-Dragon/New-Variables'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395413151770/Coiling-Dragon/Throwing-One’s-Life-AwayCD, Chapter 633': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395413151770/Coiling-Dragon/Throwing-One%E2%80%99s-Life-Away'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394600030259/Coiling-Dragon/CapturedCD, Chapter 122': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394600030259/Coiling-Dragon/Captured'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395140866082/Coiling-Dragon/Meditative-Training-BeginsCD, Chapter 378': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395140866082/Coiling-Dragon/Meditative-Training-Begins'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395413135386/Coiling-Dragon/Abyssal-MountainCD, Chapter 634': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395413135386/Coiling-Dragon/Abyssal-Mountain'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394600013875/Coiling-Dragon/The-Man-Behind-the-CurtainCD, Chapter 123': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394600013875/Coiling-Dragon/The-Man-Behind-the-Curtain'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395140849698/Coiling-Dragon/A-Visit-From-YaleCD, Chapter 379': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395140849698/Coiling-Dragon/A-Visit-From-Yale'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395413119002/Coiling-Dragon/Abyssal-FruitCD, Chapter 635': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395413119002/Coiling-Dragon/Abyssal-Fruit'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394599997491/Coiling-Dragon/The-InvestigationCD, Chapter 124': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394599997491/Coiling-Dragon/The-Investigation'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395140767778/Coiling-Dragon/A-Sudden-ChangeCD, Chapter 380': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395140767778/Coiling-Dragon/A-Sudden-Change'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395413233690/Coiling-Dragon/Haired-LadyCD, Chapter 636': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395413233690/Coiling-Dragon/Haired-Lady'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394599981107/Coiling-Dragon/Secrets-ExposedCD, Chapter 125': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394599981107/Coiling-Dragon/Secrets-Exposed'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395140751394/Coiling-Dragon/Five-YearsCD, Chapter 381': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395140751394/Coiling-Dragon/Five-Years'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395413217306/Coiling-Dragon/Snakes-and-Trees!CD, Chapter 637': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395413217306/Coiling-Dragon/Snakes-and-Trees!'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394599964723/Coiling-Dragon/ImprisonedCD, Chapter 126': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394599964723/Coiling-Dragon/Imprisoned'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395140800546/Coiling-Dragon/Mysterious-ReligionsCD, Chapter 382': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395140800546/Coiling-Dragon/Mysterious-Religions'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395413200922/Coiling-Dragon/LostCD, Chapter 638': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395413200922/Coiling-Dragon/Lost'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394599948340/Coiling-Dragon/To-Be-WrongedCD, Chapter 127': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394599948340/Coiling-Dragon/To-Be-Wronged'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395140784162/Coiling-Dragon/GuidanceCD, Chapter 383': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395140784162/Coiling-Dragon/Guidance'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395413184538/Coiling-Dragon/Green-SnakesCD, Chapter 639': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395413184538/Coiling-Dragon/Green-Snakes'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394600226866/Coiling-Dragon/LimitsCD, Chapter 128': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394600226866/Coiling-Dragon/Limits'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395141586975/Coiling-Dragon/ControlledCD, Chapter 384': {
		'type': 'translated',
		'ad_free': False,
		'language': 'unknown',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395141586975/Coiling-Dragon/Controlled'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395682947095/Coiling-Dragon/Slaughter!CD, Chapter 640': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395682947095/Coiling-Dragon/Slaughter!'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394600210482/Coiling-Dragon/The-PleaCD, Chapter 129': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394600210482/Coiling-Dragon/The-Plea'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395141570591/Coiling-Dragon/Discarding-a-PieceCD, Chapter 385': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395141570591/Coiling-Dragon/Discarding-a-Piece'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395682930711/Coiling-Dragon/A-Strange-SituationCD, Chapter 641': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395682930711/Coiling-Dragon/A-Strange-Situation'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394600259634/Coiling-Dragon/The-VisitCD, Chapter 130': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394600259634/Coiling-Dragon/The-Visit'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395141554207/Coiling-Dragon/SoulsilkCD, Chapter 386': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395141554207/Coiling-Dragon/Soulsilk'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395682979863/Coiling-Dragon/Fortune?-Misfortune?CD, Chapter 642': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395682979863/Coiling-Dragon/Fortune%3F-Misfortune%3F'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727394600243250/Coiling-Dragon/The-King-of-KillersCD, Chapter 131': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727394600243250/Coiling-Dragon/The-King-of-Killers'
	},
	'https://www.webnovel.com/rssbook/8094085105004705/21727395141537823/Coiling-Dragon/(title-hidden)CD, Chapter 387': {
		'type': 'translated',
		'ad_free': False,
		'language': 'en',
		'series_name': 'Coiling Dragon',
		'resolved_url': 'https://www.webnovel.com/book/8094085105004705/21727395141537823/Coiling-Dragon/(title-hidden)'
	}
}

def get_plugin_lut():
	log = logging.getLogger("Main.Importer")
	log.info("Testing import options")

	plugins = autotriever.plugin_loader.loadPlugins('modules', "PluginInterface_")

	return plugins

def test_storiesonline():
	try:
		settings = local_entry_point.loadSettings()
	except local_entry_point.SettingsLoadFailed:
		print("WARNING! No settings!")
		print("Cannot test storiesonline!")
		return

	instance = dispatcher.RpcCallDispatcher(settings)
	for x in range(12880, 12980):
		url = "http://storiesonline.net/s/{num}/".format(num=x)

		args = (url, )
		kwargs = {}
		try:
			ret = instance.doCall("StoriesOnlineFetch", "getpage", call_args=args, call_kwargs=kwargs, context_responder=None)
			print(ret)
		except Exception:
			pass

def tfunc(threadnum):
	print("Thread %s running" % threadnum)
	wg = WebRequest.WebGetRobust()
	print(wg)

	wg.getItemChromium("http://www.google.com")
	wg.getHeadTitleChromium("http://www.google.com")
	wg.getHeadChromium("http://www.google.com")

	print("Cookies:")
	print(wg.cj)

	print("Thread %s finished" % threadnum)


def test_custom_chrome():
	t1 = threading.Thread(target=tfunc, args=(1, ))
	t2 = threading.Thread(target=tfunc, args=(2, ))
	t3 = threading.Thread(target=tfunc, args=(3, ))
	t4 = threading.Thread(target=tfunc, args=(4, ))
	t5 = threading.Thread(target=tfunc, args=(5, ))
	t1.start()
	t2.start()
	t1.join()
	t3.start()
	t2.join()
	t4.start()
	t3.join()
	t5.start()
	t4.join()
	t5.join()



def debug_print(debug_f, plg_f):

	print("Known plugin commands:")
	for command in plg_f.keys():
		print("	", command)
	print("Known debug commands:")
	for command in debug_f.keys():
		print("	", command)



def test_smart_dispatcher():
	try:
		settings = local_entry_point.loadSettings()
	except local_entry_point.SettingsLoadFailed:
		print("WARNING! No settings!")
		print("Cannot test storiesonline!")
		return

	test_urls = [
		'http://www.google.com',
		'http://lndb.info/',
		'http://lndb.info/light_novel/Dousei_Kara_Hajimaru_Otaku_Kanojo_no_Tsukurikata',
		'http://lndb.info/light_novel/Trinity_Blood:_Reborn_on_the_Mars',
		'http://lndb.info/light_novel/Trinity_Blood:_Reborn_on_the_Mars/vol/11962',
		'https://storiesonline.net',
		'https://www.asianhobbyist.com',
		'https://www.asianhobbyist.com/mcm-370/',
		'https://www.asianhobbyist.com/oma-165/',
		'https://creativenovels.com/',
		'https://creativenovels.com/novel/my-entire-class-was-summoned-to-another-world-except-for-me/',
		'https://creativenovels.com/novel/womanizing-mage/',
		'http://gravitytales.com/',
		'http://gravitytales.com/novel/immortal-and-martial-dual-cultivation',
		'http://gravitytales.com/novel/immortal-and-martial-dual-cultivation/imdc-chapter-3',
		'https://tags.literotica.com/',
		'http://www.livejournal.com/',
		'https://www.reddit.com/r/starrankhunter/',
		'https://www.tgstorytime.com/',
		'https://www.flying-lines.com/chapter/the-evil-prince-and-his-precious-wife:the-sly-lady/c-127',
		"https://www.flying-lines.com/novel/the-evil-prince-and-his-precious-wife:the-sly-lady",
	]

	lock_dict = local_entry_point.initialize_manager()

	instance = dispatcher.RpcCallDispatcher(settings, lock_dict=lock_dict)
	for test_url in test_urls:


		args = (test_url, )
		kwargs = {}

		_ = instance.doCall("SmartWebRequest", "smartGetItem", call_args=args, call_kwargs=kwargs, context_responder=None)
		print("Called OK!")
		# print(ret)


def test_qidian():
	try:
		settings = local_entry_point.loadSettings()
		lock_dict = local_entry_point.initialize_manager()
	except local_entry_point.SettingsLoadFailed:
		print("WARNING! No settings!")
		print("Cannot test storiesonline!")
		return



	instance = dispatcher.RpcCallDispatcher(settings, lock_dict=lock_dict)
	_ = instance.doCall(
		"SmartWebRequest",
		"qidianSmartFeedFetch",
		call_args=('https://www.webnovel.com/feed/', ),
		call_kwargs={'meta' : QIDIAN_TEST_META},
		context_responder=None,
		lock_interface=None,
		)
	print("Called OK!")
	# print(ret)



CALL_LUT = {
	"test-stories-online" : test_storiesonline,
	"test-custom-chrome"  : test_custom_chrome,
	"test-dispatcher"     : dispatcher.test,
	"preproc-test"        : test_smart_dispatcher,
}

def test():


	plugin_lut = get_plugin_lut()

	if len(sys.argv) < 2:
		print("ERROR:")
		print("You must specify a plugin to test!")
		debug_print(CALL_LUT, plugin_lut)
		return

	target = sys.argv[1]

	if target in plugin_lut:
		instance = plugin_lut[target]()
		instance.test()
		print(instance)

	elif target in CALL_LUT:
		ret = None

		if len(sys.argv) >= 4:

			plug_name = sys.argv[2]
			func_name = sys.argv[3]
			ret = CALL_LUT[target](plug_name, func_name, *sys.argv[4:])
		else:
			print("You need to specify at least the plugin + function to execute to test-dispatcher")
			print("Available calls:")
			ret = CALL_LUT[target]()

		if ret:
			with open("test-out.json", "w") as fp:
				out = json.dumps(ret, indent=4)
				fp.write(out)
		else:
			print("No call response")
	else:
		print("Unknown arg!")
		debug_print(CALL_LUT, plugin_lut)



if __name__ == "__main__":
	autotriever.deps.logSetup.initLogging()
	test_qidian()
	# logging.basicConfig(level=logging.INFO)
	# test_custom_chrome()
	# test()
	# test_smart_dispatcher()
