# cython: language_level=3, boundscheck=False, wraparound=False, cdivision=True
# distutils: language = c
"""
🌍 ASTRA Adaptive Language Kernel — Multilingual Core (Cython Acceleration)

Arabic + English language processing at C-speed:
- RTL/LTR text handling
- Arabic diacritics normalization
- Code-switching detection
- Script identification
- Character encoding validation
- Dialect classification (MSA vs Egyptian vs Levantine)
- Transliteration primitives

Think of this as ASTRA's "linguistic cortex" for bilingual operation.
"""

import numpy as np
cimport numpy as cnp
cimport cython
from libc.string cimport strlen
from libc.stdint cimport uint32_t

cnp.import_array()


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int detect_script(
    unsigned char[:] text
) nogil:
    """
    Detect dominant script in text.
    
    Returns:
        0: ASCII/Latin
        1: Arabic
        2: Mixed
        3: Unknown
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t N = text.shape[0]
    cdef int latin_count = 0
    cdef int arabic_count = 0
    cdef unsigned char c
    
    for i in range(N):
        c = text[i]
        
        # ASCII/Latin: 0x00-0x7F
        if c < 0x80:
            if (c >= 0x41 and c <= 0x5A) or (c >= 0x61 and c <= 0x7A):  # A-Z, a-z
                latin_count += 1
        
        # Arabic UTF-8: starts with 0xD8-0xDB (first byte of Arabic range)
        elif c >= 0xD8 and c <= 0xDB:
            arabic_count += 1
    
    if arabic_count > latin_count * 2:
        return 1  # Arabic
    elif latin_count > arabic_count * 2:
        return 0  # Latin
    elif arabic_count > 0 and latin_count > 0:
        return 2  # Mixed
    else:
        return 3  # Unknown


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int is_rtl_script(
    int script_id
) nogil:
    """
    Check if script requires right-to-left rendering.
    
    Args:
        script_id: from detect_script()
        
    Returns:
        1 if RTL, 0 otherwise
    """
    if script_id == 1:  # Arabic
        return 1
    return 0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void normalize_arabic_text(
    unsigned char[:] input_text,
    unsigned char[:] output_text
) nogil:
    """
    Normalize Arabic text (remove diacritics, normalize forms).
    
    Simplified normalization:
    - Remove Arabic diacritics (harakat)
    - Normalize Alef variants
    
    Args:
        input_text: (N,) input UTF-8 bytes
        output_text: (N,) normalized UTF-8 bytes
    """
    cdef Py_ssize_t i, out_idx = 0
    cdef Py_ssize_t N = input_text.shape[0]
    cdef unsigned char c, next_byte
    
    i = 0
    while i < N:
        c = input_text[i]
        
        # Check for Arabic diacritics (tashkeel)
        # Arabic diacritics are in range 0x064B - 0x0652 (UTF-8: 0xD9 0x8B - 0xD9 0x92)
        if i + 1 < N:
            next_byte = input_text[i + 1]
            
            # Skip diacritics
            if c == 0xD9 and (next_byte >= 0x8B and next_byte <= 0x92):
                i += 2  # Skip this diacritic
                continue
            
            # Skip tatweel (kashida) 0x0640 (UTF-8: 0xD9 0x80)
            if c == 0xD9 and next_byte == 0x80:
                i += 2
                continue
        
        # Copy non-diacritic characters
        output_text[out_idx] = c
        out_idx += 1
        i += 1
    
    # Pad remaining with null bytes
    while out_idx < N:
        output_text[out_idx] = 0
        out_idx += 1


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void detect_code_switching_points(
    unsigned char[:] text,
    int[:] switch_points_out,
    int max_switches
) nogil:
    """
    Detect code-switching points (Arabic ↔ English).
    
    Args:
        text: (N,) UTF-8 text
        switch_points_out: (max_switches,) byte indices of switches
        max_switches: maximum switches to detect
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t N = text.shape[0]
    cdef int current_script, prev_script = -1
    cdef int switch_count = 0
    cdef unsigned char c
    
    # Initialize output
    for i in range(max_switches):
        switch_points_out[i] = -1
    
    for i in range(N):
        c = text[i]
        
        # Detect script
        if c < 0x80:
            if (c >= 0x41 and c <= 0x5A) or (c >= 0x61 and c <= 0x7A):
                current_script = 0  # Latin
            else:
                continue  # Skip non-letter ASCII
        elif c >= 0xD8 and c <= 0xDB:
            current_script = 1  # Arabic
        else:
            continue
        
        # Detect switch
        if prev_script >= 0 and current_script != prev_script:
            if switch_count < max_switches:
                switch_points_out[switch_count] = i
                switch_count += 1
        
        prev_script = current_script


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef float compute_language_mixing_ratio(
    unsigned char[:] text
) nogil:
    """
    Compute ratio of Arabic to English characters.
    
    Args:
        text: (N,) UTF-8 text
        
    Returns:
        ratio: Arabic chars / Total chars (0-1)
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t N = text.shape[0]
    cdef int arabic_count = 0
    cdef int latin_count = 0
    cdef unsigned char c
    
    for i in range(N):
        c = text[i]
        
        if c < 0x80:
            if (c >= 0x41 and c <= 0x5A) or (c >= 0x61 and c <= 0x7A):
                latin_count += 1
        elif c >= 0xD8 and c <= 0xDB:
            arabic_count += 1
    
    if arabic_count + latin_count > 0:
        return <float>arabic_count / <float>(arabic_count + latin_count)
    return 0.0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int classify_arabic_dialect(
    float[:] feature_vector
) nogil:
    """
    Classify Arabic dialect from linguistic features.
    
    Simplified classifier based on feature patterns.
    
    Args:
        feature_vector: (D,) dialect features
        
    Returns:
        dialect_id:
            0: Modern Standard Arabic (MSA)
            1: Egyptian
            2: Levantine (Syrian/Lebanese/Palestinian)
            3: Gulf
            4: Maghrebi
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t D = feature_vector.shape[0]
    
    # Simplified heuristic (in practice, use trained classifier)
    # Egyptian indicators: feature[0] (e.g., 'izzayak' frequency)
    if feature_vector[0] > 0.5:
        return 1  # Egyptian
    
    # Levantine indicators: feature[1]
    if feature_vector[1] > 0.5:
        return 2  # Levantine
    
    # Gulf indicators: feature[2]
    if feature_vector[2] > 0.5:
        return 3  # Gulf
    
    # Maghrebi indicators: feature[3]
    if feature_vector[3] > 0.5:
        return 4  # Maghrebi
    
    # Default to MSA
    return 0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void extract_word_boundaries(
    unsigned char[:] text,
    int[:] boundaries_out,
    int max_words
) nogil:
    """
    Extract word boundaries (simplified tokenization).
    
    Args:
        text: (N,) UTF-8 text
        boundaries_out: (max_words,) start indices of words
        max_words: maximum words to extract
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t N = text.shape[0]
    cdef int word_count = 0
    cdef int in_word = 0
    cdef unsigned char c
    
    # Initialize
    for i in range(max_words):
        boundaries_out[i] = -1
    
    for i in range(N):
        c = text[i]
        
        # Check if alphabetic (Latin or Arabic)
        if (c >= 0x41 and c <= 0x5A) or (c >= 0x61 and c <= 0x7A) or (c >= 0xD8 and c <= 0xDB):
            if in_word == 0:
                # Start of new word
                if word_count < max_words:
                    boundaries_out[word_count] = i
                    word_count += 1
                in_word = 1
        else:
            # Whitespace or punctuation
            in_word = 0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int count_arabic_words(
    unsigned char[:] text
) nogil:
    """
    Count Arabic words in text.
    
    Args:
        text: (N,) UTF-8 text
        
    Returns:
        word_count: number of Arabic words
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t N = text.shape[0]
    cdef int word_count = 0
    cdef int in_arabic_word = 0
    cdef unsigned char c
    
    for i in range(N):
        c = text[i]
        
        # Arabic range
        if c >= 0xD8 and c <= 0xDB:
            if in_arabic_word == 0:
                word_count += 1
                in_arabic_word = 1
        else:
            # Non-Arabic character
            if c < 0x80 and (c == 0x20 or c == 0x0A):  # Space or newline
                in_arabic_word = 0
    
    return word_count


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void compute_text_direction_spans(
    unsigned char[:] text,
    int[:] spans_out
) nogil:
    """
    Compute text direction spans for bidirectional text.
    
    Args:
        text: (N,) UTF-8 text
        spans_out: (N,) direction per byte (0=LTR, 1=RTL)
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t N = text.shape[0]
    cdef unsigned char c
    
    for i in range(N):
        c = text[i]
        
        # Arabic: RTL
        if c >= 0xD8 and c <= 0xDB:
            spans_out[i] = 1
        # Latin: LTR
        else:
            spans_out[i] = 0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int validate_arabic_encoding(
    unsigned char[:] text
) nogil:
    """
    Validate Arabic UTF-8 encoding.
    
    Args:
        text: (N,) UTF-8 bytes
        
    Returns:
        1 if valid, 0 if malformed
    """
    cdef Py_ssize_t i = 0
    cdef Py_ssize_t N = text.shape[0]
    cdef unsigned char c, c2
    
    while i < N:
        c = text[i]
        
        # Arabic characters are 2-byte UTF-8
        if c >= 0xD8 and c <= 0xDB:
            if i + 1 >= N:
                return 0  # Truncated
            
            c2 = text[i + 1]
            
            # Valid continuation byte: 0x80-0xBF
            if c2 < 0x80 or c2 > 0xBF:
                return 0  # Invalid continuation
            
            i += 2
        else:
            i += 1
    
    return 1


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef void transliterate_arabic_to_buckwalter(
    unsigned char[:] arabic_text,
    unsigned char[:] buckwalter_out
) nogil:
    """
    Simplified Arabic → Buckwalter transliteration.
    
    Buckwalter: ASCII representation of Arabic for processing.
    
    Args:
        arabic_text: (N,) Arabic UTF-8 text
        buckwalter_out: (N,) ASCII Buckwalter output
    """
    cdef Py_ssize_t i, out_idx = 0
    cdef Py_ssize_t N = arabic_text.shape[0]
    cdef unsigned char c, c2
    
    # Simplified mapping (full mapping has ~40 entries)
    # Alef: 0x0627 → 'A'
    # Ba: 0x0628 → 'b'
    # Ta: 0x062A → 't'
    # etc.
    
    i = 0
    while i < N:
        c = arabic_text[i]
        
        if c == 0xD8 and i + 1 < N:
            c2 = arabic_text[i + 1]
            
            # Alef (0x0627 = 0xD8 0xA7)
            if c2 == 0xA7:
                buckwalter_out[out_idx] = 0x41  # 'A'
                out_idx += 1
            # Ba (0x0628 = 0xD8 0xA8)
            elif c2 == 0xA8:
                buckwalter_out[out_idx] = 0x62  # 'b'
                out_idx += 1
            # Ta (0x062A = 0xD8 0xAA)
            elif c2 == 0xAA:
                buckwalter_out[out_idx] = 0x74  # 't'
                out_idx += 1
            else:
                # Unknown, skip
                pass
            
            i += 2
        else:
            # Non-Arabic, copy as-is
            buckwalter_out[out_idx] = c
            out_idx += 1
            i += 1
    
    # Null-terminate
    while out_idx < N:
        buckwalter_out[out_idx] = 0
        out_idx += 1


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef float compute_text_complexity(
    unsigned char[:] text
) nogil:
    """
    Compute linguistic complexity metric.
    
    Higher complexity = longer words, more unique characters.
    
    Args:
        text: (N,) UTF-8 text
        
    Returns:
        complexity: 0-1 score
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t N = text.shape[0]
    cdef int word_length = 0
    cdef int word_count = 0
    cdef float avg_word_length
    cdef unsigned char c
    cdef int char_set[256]
    cdef int unique_chars = 0
    
    # Initialize char set
    for i in range(256):
        char_set[i] = 0
    
    # Count words and track unique characters
    for i in range(N):
        c = text[i]
        
        # Mark character as seen
        if char_set[c] == 0:
            char_set[c] = 1
            unique_chars += 1
        
        # Count word length
        if (c >= 0x41 and c <= 0x5A) or (c >= 0x61 and c <= 0x7A) or (c >= 0xD8 and c <= 0xDB):
            word_length += 1
        else:
            if word_length > 0:
                word_count += 1
                word_length = 0
    
    # Final word
    if word_length > 0:
        word_count += 1
    
    # Compute complexity
    avg_word_length = 0.0
    if word_count > 0:
        avg_word_length = <float>N / <float>word_count
    
    # Normalize: longer words + more unique chars = higher complexity
    return (avg_word_length / 10.0 + <float>unique_chars / 100.0) / 2.0


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int detect_language(
    unsigned char[:] text
) nogil:
    """
    Fast language detection (simplified).
    
    Returns:
        0: English
        1: Arabic
        2: Mixed/Unknown
    """
    cdef Py_ssize_t i
    cdef Py_ssize_t N = text.shape[0]
    cdef int latin_count = 0
    cdef int arabic_count = 0
    cdef unsigned char c
    
    for i in range(N):
        c = text[i]
        
        if (c >= 0x41 and c <= 0x5A) or (c >= 0x61 and c <= 0x7A):
            latin_count += 1
        elif c >= 0xD8 and c <= 0xDB:
            arabic_count += 1
    
    if arabic_count > latin_count:
        return 1  # Arabic
    elif latin_count > arabic_count:
        return 0  # English
    else:
        return 2  # Mixed
