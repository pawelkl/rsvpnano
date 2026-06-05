#pragma once

#include <Arduino.h>
#include <cstring>

#include "text/LatinText.h"

namespace WordGlue {

inline bool isLexiconWord(const String &word) {
  static constexpr const char *kWords[] = {
      // English
      "a",    "am",   "an",   "and",  "are",  "as",   "at",   "be",  "but",
      "by",   "do",   "for",  "from", "had",  "has",  "he",   "her", "his",
      "i",    "if",   "in",   "is",   "it",   "me",   "my",   "no",  "not",
      "of",   "on",   "or",   "she",  "so",   "that", "the",  "to",  "was",
      "we",   "were", "with", "you",

      // Spanish
      "a",    "al",   "como", "con",  "de",   "del",  "el",   "en",  "es",
      "la",   "las",  "lo",   "los",  "me",   "mi",   "no",   "por", "que",
      "se",   "si",   "su",   "te",   "un",   "una",  "y",

      // French
      "a",    "au",   "aux",  "ce",   "ces",  "dans", "de",   "des", "du",
      "elle", "en",   "est",  "et",   "il",   "je",   "la",   "le",  "les",
      "ma",   "mais", "me",   "ne",   "nous", "pas",  "pour", "que", "qui",
      "se",   "son",  "sur",  "tu",   "un",   "une",  "vous",

      // German
      "aber", "als",  "am",   "an",   "auf",  "aus",  "das",  "dem", "den",
      "der",  "des",  "die",  "du",   "ein",  "eine", "er",   "es",  "ich",
      "im",   "in",   "ist",  "mit",  "nicht", "sie", "und",  "von", "war",
      "zu",

      // Romanian
      "a",    "ai",   "am",   "are",  "ca",   "ce",   "cu",   "de",  "din",
      "e",    "ea",   "ei",   "el",   "era",  "este", "eu",   "in",  "la",
      "mai",  "ma",   "mi",   "nu",   "o",    "pe",   "sa",   "se",  "si",
      "te",   "un",   "una",

      // Polish
      "a",    "ale",  "bez",  "bo",   "by",   "byl",  "byla", "bylo", "co",
      "czy",  "dla",  "do",   "go",   "i",    "ja",   "jak",  "je",   "jej",
      "jego", "jest", "juz",  "mi",   "mnie", "na",   "nie",  "o",    "od",
      "on",   "ona",  "po",   "pod",  "przez", "sie", "ta",   "tak",  "te",
      "tego", "ten",  "to",   "tu",   "tym",  "w",    "we",   "z",    "za",
      "ze"};

  for (const char *entry : kWords) {
    if (std::strcmp(word.c_str(), entry) == 0) {
      return true;
    }
  }
  return false;
}

inline bool foldedWord(const String &token, String &folded) {
  folded = "";
  folded.reserve(token.length());
  for (size_t i = 0; i < token.length(); ++i) {
    const uint8_t value = LatinText::byteValue(token[i]);
    if (!LatinText::isWordCharacter(value) && !LatinText::isLowCustomSlotByte(value)) {
      folded = "";
      return false;
    }
    const uint8_t lower = LatinText::toLowercaseByte(value);
    const uint8_t ascii = LatinText::fallbackAsciiByte(lower);
    if (!((ascii >= 'a' && ascii <= 'z') || (ascii >= '0' && ascii <= '9'))) {
      folded = "";
      return false;
    }
    folded += static_cast<char>(ascii);
  }
  return true;
}

inline bool splitGluedToken(const String &token, String &first, String &second) {
  first = "";
  second = "";
  if (token.length() < 5 || token.length() > 18) {
    return false;
  }

  String folded;
  if (!foldedWord(token, folded)) {
    return false;
  }

  for (size_t split = 2; split + 2 <= folded.length(); ++split) {
    const String left = folded.substring(0, split);
    const String right = folded.substring(split);
    if (!isLexiconWord(left) || !isLexiconWord(right)) {
      continue;
    }

    first = token.substring(0, split);
    second = token.substring(split);
    return true;
  }

  return false;
}

}  // namespace WordGlue
