﻿#synthDrivers/newfon.py
#A part of NonVisual Desktop Access (NVDA)
#Copyright (C) 2006-2008 NVDA Contributors <http://www.nvda-project.org/>
#This file is covered by the GNU General Public License.
#See the file COPYING for more details.
from synthDriverHandler import SynthDriver,VoiceInfo
from ctypes import *
import os
import config
import nvwave
import re
from logHandler import log

#config
abbreviationsLength = 4

isSpeaking = False
player = None
ProcessAudioCallback = WINFUNCTYPE(c_int, POINTER(c_char),POINTER(c_char),c_int)

@ProcessAudioCallback
def processAudio(udata, buffer,length):
	global isSpeaking,player
	if not isSpeaking: return 1
	player.feed(string_at(buffer, length))
	return 0

re_words = re.compile(r"\b(\w+)\b",re.U)
re_abbreviations = re.compile(r"\b([bcdfghjklmnpqrstvwxz]+)\b")
re_afterNumber = re.compile(r"(\d+)([^\.\:\-\/\!\?\d])")
re_ukrainianApostrophe=re.compile(ur"'([яюєї])",re.I)
re_omittedCharacters = re.compile(r"[\(\)\*_\"]+")

letters = {
'a': u"эй",
'b' : u"би",
'c': u"си",
'd': u"ди",
'e': u"и",
'f': u"эф",
'g': u"джи",
'h': u"эйчь",
'i': u"ай",
'j': u"джей",
'k': u"кэй",
'l': u"эль",
'm': u"эм",
'n': u"эн",
'o': u"оу",
'p': u"пи",
'q': u"къю",
'r': u"ар",
's': u"эс",
't': u"ти",
'u': u"ю",
'v': u"ви",
'w': u"да+блъю",
'x': u"экс",
'y': u"вай",
'z': u"зи",
u"б": u"бэ",
u"в": u"вэ",
u"к": u"ка",
u"с": u"эс",
u"ь": u"мя",
u"ъ": u"твё"
}

englishPronunciation= {
'x': u"кс",
'e': u"э",
'y': u"ы",
'j': u"дж"
}
#ukrainian to russian character map
#ukrainian soft "g" is not supported, becouse synth does not contain this phonem :(
ukrainianPronunciation = {
u"и": u"ы",
u"і": u"и",
u"ї": u"ййи",
u"е": u"э",
u"є": u"йе",
u"ц": u"тс"
}
ukrainianPronunciationA = [u"и", u"і",u"ї",u"е",u"є",u"ц"]

def processWords(match):
	l = len(match.group(1))
	loweredText = match.group(1).lower()
	if l == 1:
		return letters[loweredText] if letters.has_key(loweredText) else loweredText
	if (match.group(1).isupper() and l <= abbreviationsLength) or re_abbreviations.match(loweredText):
		expandedText = ""
		for letter in loweredText:
			expandedText += letters[letter] if letters.has_key(letter) else letter
			if letter.isalpha(): expandedText+=" "
		return expandedText
	for s in englishPronunciation:
		loweredText = loweredText.replace(s, englishPronunciation[s])
	return loweredText

def preprocessEnglishText(text):
	return re_words.sub(processWords, text)

def preprocessUkrainianText(text):
	if len(text) == 1:
		return ukrainianPronunciation[text] if ukrainianPronunciation.has_key(text) else text
	text = re_ukrainianApostrophe.sub(u"ь\\1", text)
	for s in ukrainianPronunciationA:
		text = text.replace(s, ukrainianPronunciation[s])
	return text

class SynthDriver(SynthDriver):
	name="newfon"
	description = _("russian newfon synthesizer by Sergey Shishmintzev")
	hasVoice=True
	hasVolume = True
	hasRate=True
	hasVariant=True
	_volume = 100
	_variant="rus"
	hasPitch = True
	_pitch = 50
	_rate=70
	availableVoices = (VoiceInfo("0", _("male 1")), VoiceInfo("1", _("female 1")), VoiceInfo("2", _("male 2")), VoiceInfo("3", _("female 2")))
	availableVariants = (VoiceInfo("rus", u"русский"), VoiceInfo("ukr", u"український"))
	newfon_lib = None
	sdrvxpdbDll = None
	dictDll = None

	@classmethod
	def check(cls):
		return os.path.isfile('synthDrivers/newfon_nvda.dll')

	def __init__(self):
		global player
		player = nvwave.WavePlayer(channels=1, samplesPerSec=10000, bitsPerSample=8, outputDevice=config.conf["speech"]["outputDevice"])
		self.hasDictLib = os.path.isfile('synthDrivers/dict.dll')
		if self.hasDictLib:
			self.sdrvxpdb_lib = windll.LoadLibrary(r"synthDrivers\sdrvxpdb.dll")
			self.dict_lib = windll.LoadLibrary(r"synthDrivers\dict.dll")
		self.newfon_lib = windll.LoadLibrary(r"synthDrivers\newfon_nvda.dll")
		self.newfon_lib.speakText.argtypes = [c_char_p, c_int]
		if not self.newfon_lib.initialize(): raise Exception
		self.newfon_lib.set_callback(processAudio)

	def terminate(self):
		self.cancel()
		global player
		player.close()
		player=None
		self.newfon_lib.terminate()
		del self.newfon_lib
		if self.hasDictLib:
			del self.dict_lib
			del self.sdrvxpdb_lib

	def speakText(self, text, index=None):
		global isSpeaking
		isSpeaking = True
		text = re_omittedCharacters.sub(" ", text)
		text = re_afterNumber.sub(r"\1-\2", text)
		if self._variant == "ukr":
			text = preprocessUkrainianText(text)
		text = preprocessEnglishText(text)
		if index is not None: 
			self.newfon_lib.speakText(text,index)
		else:
			self.newfon_lib.speakText(text,-1)

	def _get_lastIndex(self):
		return self.newfon_lib.get_lastIndex()

	def cancel(self):
		self.newfon_lib.cancel()
		global isSpeaking,player
		isSpeaking = False
		player.stop()

	def _get_voice(self):
		return str(self.newfon_lib.get_voice())

	def _set_voice(self, value):
		self.newfon_lib.set_voice(int(value))

	def _get_volume(self):
		return self._volume

	def _set_volume(self,value):
		self.newfon_lib.set_volume(value)
		self._volume = value

	def _get_rate(self):
		return self._rate

	def _set_rate(self, value):
		self.newfon_lib.set_rate(value)
		self._rate = value

	def _set_pitch(self, value):
		if value <= 50: value = 50
		self.newfon_lib.set_accel(value/5 -10 )
		self._pitch = value

	def _get_pitch(self):
		return self._pitch

	def pause(self, switch):
		global player
		player.pause(switch)

	def _get_variant(self):
		return self._variant

	def _set_variant(self, variant):
		self._variant = variant
		if not self.hasDictLib: return
		if variant == "rus": self.newfon_lib.set_dictionary(1)
		else: self.newfon_lib.set_dictionary(0)
