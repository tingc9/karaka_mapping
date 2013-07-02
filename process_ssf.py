#!/usr/bin/env python
"""
Classes to process and store SSF files/elements.
Copyright (C) 2013  Nikhilesh Bhatnagar

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import os
import re
import logging

# authorship information
__author__ = "Nikhilesh Bhatnagar"
__credits__ = ["Nikhilesh Bhatnagar"]
__license__ = None
__version__ = "0.1"
__maintainer__ = "Nikhilesh Bhatnagar"
__email__ = "nikhilesh.bhatnagar@research.iiit.ac.in"
__status__ = "Prototype"
# global initialization
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# so that multiple handlers for the same file are made
# remember, logging is a global object, so its not remade for the same name
if not logger.hasHandlers():
	handler = logging.FileHandler('mapper/logs/process_ssf.log')
	handler.setLevel(logging.DEBUG)
	formatter = logging.Formatter('%(asctime)s - %(name)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s')
	handler.setFormatter(formatter)
	logger.addHandler(handler)


# class representing a SSF token with the feature structure, POS and ID information (in any case machine dynamic ID is provided in case of null IDs)
class ssf_token(object):
	current_available_id = 0

	def __init__(self, parent_chunk, ssf_token_string):
		# assign parent link
		self.parent = parent_chunk
		# validity checks:
		# token must be fully qualified with number, type and feature structure
		try:
			self.ssf_token_number = ssf_token_string.split("\n")[0].split("\t")[0]
		except IndexError:
			self.ssf_token_value = ""
			logger.warning("Token number not valid.")
			return
		try:
			self.ssf_token_value = ssf_token_string.split("\n")[0].split("\t")[1]
		except IndexError:
			self.ssf_token_value = ""
			logger.warning("Token value not valid.")
			return
		try:
			self.ssf_token_type = ssf_token_string.split("\n")[0].split("\t")[2]
		except IndexError:
			self.ssf_token_value = ""
			logger.warning("Token type not valid.")
			return
		# in some cases, more than one feature structure exist for tokens, so need to take care of that
		# slicing to shave off '<fs ' in the feature string at start and > at the end
		if "<fs" in ssf_token_string:
			feature_structures = [feature_structure_string[4:-1].split() for feature_structure_string in ssf_token_string.split("\n")[0].split("\t")[3].split("|")]
		# broken SSF where fs starts like <af=...
		elif "=" in ssf_token_string and "fs" not in ssf_token_string:
			feature_structures = [feature_structure_string[1:-1].split() for feature_structure_string in ssf_token_string.split("\n")[0].split("\t")[3].split("|")]
		# even process SSF token with no feature structure
		else:
			feature_structures = []
		self.ssf_feature_structure = {}
		# for every feature structure check existence of lhs value such as af and put the rhs string in the dict
		# TODO split the rhs string and structure that also
		for feature_structure in feature_structures:
			for feature in feature_structure:
				if "af" in feature:
					try:
						# remove ' from the features for simplicity and consistency
						self.ssf_feature_structure[feature.split("=")[0]] = feature.split("=")[1].strip("'").strip("\"").split(",")
					except IndexError:
						self.ssf_token_value = ""
						logger.warning("Token feature structure problem encountered!")
						break
				else:
					try:
						# remove ' from the features for simplicity and consistency
						self.ssf_feature_structure[feature.split("=")[0]] = feature.split("=")[1].strip("'").strip("\"")
					except IndexError:
						self.ssf_token_value = ""
						logger.warning("Token feature structure problem encountered!")
						break
		#Assign dynamic unique ID and update it
		self.id = ssf_token.current_available_id
		ssf_token.current_available_id += 1


# class representing a SSF chunk with the feature structure, chunk tag and ID information (in any case machine dynamic ID is provided in case of null IDs)
# BEWARE SSF tagged chunks are ignored.
class ssf_chunk(object):
	current_available_id = 0

	def __init__(self, parent_sentence, ssf_chunk_string):
		# setup parent link
		self.parent = parent_sentence
		self.ssf_tokens_and_chunks = []
		# not converting ssf_chunk_number to integer because we can have stuff like 1.2.3
		self.ssf_chunk_number = ssf_chunk_string.split("\n")[0].split("\t")[0]
		self.ssf_chunk_type = ssf_chunk_string.split("\n")[0].split("\t")[2]
		# remove '<fs ' and '>' from the feature structure string
		# process SSF chunks with no feature structure. They sometimes occur with well made chunks as well owing to inconsistent annotation.
		try:
			feature_structures = ssf_chunk_string.split("\n")[0].split("\t")[3][4:-1].split()
		except IndexError:
			feature_structures = []
		self.ssf_feature_structure = {}
		for feature_structure in feature_structures:
			# remove ' from the features for simplicity and consistency
			self.ssf_feature_structure[feature_structure.split("=")[0]] = feature_structure.split("=")[1].strip("'").strip("\"")
		# checks for level of nesting in the loop below
		nesting = 0
		# current chunk consists of lines in the ssf_chunk_string which encapsulates the current inner or outer chunk
		current_chunk = ""
		#Remove first and last line so that main chunk is not counted as nested chunk
		for line in ssf_chunk_string.split("\n")[1:-1]:
			if "((" in line:
				# an inner chunk has started (since we already removed the top line containing '((')
				current_chunk += line + "\n"
				nesting += 1
			elif "))" in line:
				# current chunk has completed
				current_chunk += line + "\n"
				nesting -= 1
				# check if it was nested or not
				if nesting == 0:
					# remove trailing \n from current_chunk
					# this constructor is a recursive call for the nested chunks
					ssf_chunk_object = ssf_chunk(self, current_chunk[:-1])
					# if the chunk has chunks or tokens, it is valid
					if len(ssf_chunk_object.ssf_tokens_and_chunks) > 0:
						self.ssf_tokens_and_chunks.append(ssf_chunk_object)
					# reset current_chunk
					current_chunk = ""
			else:
				# it is a token
				# check if the token in a nested chunk or in the main chunk string for this object
				if nesting == 0:
					# token in main chunk
					ssf_token_object = ssf_token(self, line)
					# if the token has a token and the feature structure, it is valid
					# for tokens, validation is over equality as this is the ground step which blows up to the sentence level
					if ssf_token_object.ssf_token_value == "":
						# blow up the stack!!
						self.ssf_tokens_and_chunks = []
						break
					else:
						self.ssf_tokens_and_chunks.append(ssf_token_object)
				else:
					# token in nested chunk
					current_chunk += line + "\n"
		# assign dynamic unique ID and update it
		self.id = ssf_chunk.current_available_id
		ssf_chunk.current_available_id += 1

	def tokens(self):
		token_list = []
		for element in self.ssf_tokens_and_chunks:
			if type(element) == ssf_token:
				token_list.append(element)
			else:
				token_list += element.tokens()
		return token_list


#Class representing a SSF sentence with ID information (in any case machine dynamic ID is provided in case of null IDs)
class ssf_sentence(object):
	current_available_id = 0

	def __init__(self, parent_document, ssf_sentence_string):
		# make parent object link
		self.parent = parent_document
		# list of all ssf_chunk objects in the sentence
		self.ssf_chunks = []
		# validate the sentence structure also
		# like with documents, did not encounter any other string than id=, maybe it needs to be changed in the future
		# replaced [\w\W]+ with [\w\W]* in regex, if unexpected problems arise, switch back
		try:
			ssf_sentence_id, ssf_sentence_inner = re.findall("<Sentence id=(?:\"|')(.*?)(?:\"|')>([\w\W]*?</)Sentence>", ssf_sentence_string)[0]
		except IndexError:
			return
		# ID given in SSF format, could be null also
		self.ssf_id = ssf_sentence_id
		# send the chunk so that it can be validated and the object made; the regex is used to ensure that only one chunk reaches the ssf_chunk constructor
		# only outermost chunk is selected; nested chunks deferred to ssf_chunk class because tokens and chunks can be mixed in a nested chunk
		# FIXED chunks with tokens after nested chunks are processed correctly
		# regex cannot do bracket matching
		for ssf_chunk_string in self.get_chunk_strings(ssf_sentence_string):
			ssf_chunk_object = ssf_chunk(self, ssf_chunk_string)
			# if the chunk has chunks or tokens, it is valid
			if len(ssf_chunk_object.ssf_tokens_and_chunks) > 0:
				self.ssf_chunks.append(ssf_chunk_object)
		# assign dynamic unique ID and update it
		self.id = ssf_sentence.current_available_id
		ssf_sentence.current_available_id += 1

	# fuction to return outermost chunk strings with brackets
	def get_chunk_strings(self, sentence_string):
		# remove <Sentence> tags
		sentence_string = "\n".join(sentence_string.split("\n")[1:-1])
		# remove SSF chunk
		# BEWARE SSF chunk (normally chunk 0) is removed
		if "SSF" in sentence_string.split("\n")[1]:
			sentence_string = "\n".join(sentence_string.split("\n")[1:-1])
		# track brackets to separate outer chunks
		bracket_counter = 0
		chunk_strings = []
		current_chunk_string = ""
		for line in sentence_string.split("\n"):
			if "((" in line:
				current_chunk_string += line + "\n"
				bracket_counter += 1
			elif "))" in line:
				current_chunk_string += line + "\n"
				bracket_counter -= 1
			else:
				current_chunk_string += line + "\n"
			if bracket_counter == 0:
				chunk_strings.append(current_chunk_string)
				# reset current chunk string
				current_chunk_string = ""
		return chunk_strings

	def chunks(self, mode="outer"):
		chunk_list = []
		# outer mode when level 1 i.e. just below SSF chunk
		chunk_list += self.ssf_chunks
		if mode == "inner" or mode == "all":
			# set stack and completed list
			temp_chunk_list = chunk_list
			chunk_list = []
			while len(temp_chunk_list) > 0:
				curr_chunk = temp_chunk_list[-1]
				sub_chunks = [sub_chunk for sub_chunk in temp_chunk_list[-1].ssf_tokens_and_chunks if type(sub_chunk) == ssf_chunk]
				if mode == "inner":
					if len(sub_chunks) == 0:
						chunk_list.append(temp_chunk_list[-1])
				elif mode == "all":
					chunk_list.append(temp_chunk_list[-1])
				temp_chunk_list.pop()
				temp_chunk_list += sub_chunks
			chunk_list.reverse()
		return chunk_list


# class representing a SSF document with ID information (in any case machine dynamic ID is provided in case of null IDs)
class ssf_document(object):
	current_available_id = 0

	def __init__(self, parent_corpus, ssf_document_string, document_file_path, mode="lax"):
		# set path and parent link
		self.path = document_file_path
		self.parent = parent_corpus
		# list of ssf_sentence objects in the document
		self.ssf_sentences = []
		# lax mode is where the sentences are not actually in document tags but are present
		if mode == "lax":
			# special document ID
			self.ssf_id = "null_lax"
			# send the sentence so that it can be validated and the object made; the regex is applied here to ensure that only one sentence reaches the ssf_sentence constructor
			# replaced [\w\W]+ with [\w\W]* in regex, if unexpected problems arise, switch back
			for ssf_sentence_string in re.findall("<Sentence[\w\W]*?</Sentence>", ssf_document_string):
				ssf_sentence_object = ssf_sentence(self, ssf_sentence_string)
				# if the sentence has chunks, it is valid
				if len(ssf_sentence_object.ssf_chunks) > 0:
					self.ssf_sentences.append(ssf_sentence_object)
		else:
			# this mode assumes that proper document tag encapsulation is present
			# replaced [\w\W]+ with [\w\W]* in regex, if unexpected problems arise, switch back
			ssf_document_id, ssf_document_content = re.findall("<document (?:doc)?id=(?:\"|')(.*?)(?:\"|')>([\w\W]*?)</document>", ssf_document_string)[0]
			# ID given in SSF format, sometimes it can be null also
			self.ssf_id = ssf_document_id
			# send the sentence so that it can be validated and the object made; the regex is applied here to ensure that only one sentence reaches the ssf_sentence constructor
			# replaced [\w\W]+ with [\w\W]* in regex, if unexpected problems arise, switch back
			for ssf_sentence_string in re.findall("<Sentence[\w\W]*?</Sentence>", ssf_document_content):
				ssf_sentence_object = ssf_sentence(self, ssf_sentence_string)
				# if the sentence has chunks, it is valid
				if len(ssf_sentence_object.ssf_chunks) > 0:
					self.ssf_sentences.append(ssf_sentence_object)
		# assign dynamic unique ID and update it
		self.id = ssf_document.current_available_id
		ssf_document.current_available_id += 1

	def sentences(self):
		# return all sentences in the document
		return self.ssf_sentences


# class representing a SSF corpus with ID information (in any case machine dynamic ID is provided in case of null IDs)
class ssf_corpus(object):
	current_available_id = 0

	def __init__(self, ssf_corpus_folder, mode="lax"):
		# set path and parent link
		self.path = os.path.abspath(ssf_corpus_folder)
		# list of ssf_document objects in this corpus
		self.ssf_documents = []
		for ssf_corpus_file in os.listdir(ssf_corpus_folder):
			ssf_corpus_file_handle = open(ssf_corpus_folder + ssf_corpus_file, "r")
			# send the document so that it can be validated and the object made; the regex is applied here to ensure that only one document reaches the ssf_document constructor
			ssf_corpus_text = ssf_corpus_file_handle.read()
			# replaced [\w\W]+ with [\w\W]* in regex, if unexpected problems arise, switch back
			ssf_document_string_list = re.findall("<document[\w\W]*?</document>", ssf_corpus_text)
			for ssf_document_string in ssf_document_string_list:
				ssf_document_object = ssf_document(self, ssf_document_string, os.path.abspath(ssf_corpus_folder + ssf_corpus_file), mode="strict")
				# if the document has sentences, it is valid
				if len(ssf_document_object.ssf_sentences) > 0:
					self.ssf_documents.append(ssf_document_object)
			if mode == "lax":
				# assume each document is a bunch of sentences not encapsulated in document tags
				ssf_document_string = ssf_corpus_text
				if len(ssf_document_string_list) == 0:
					ssf_document_object = ssf_document(self, ssf_document_string, os.path.abspath(ssf_corpus_folder + ssf_corpus_file))
					# if the document has sentences, it is valid
					if len(ssf_document_object.ssf_sentences) > 0:
						self.ssf_documents.append(ssf_document_object)
			ssf_corpus_file_handle.close()
		# assign dynamic unique ID and update it
		self.id = ssf_corpus.current_available_id
		ssf_corpus.current_available_id += 1

	def documents(self):
		#return all documents in the corpus
		return self.ssf_documents
