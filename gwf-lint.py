#!/usr/bin/env python 

import sys
import os
import getopt
import urlparse
import re
# import kwval
# from fontTools import ttLib

# Line 13 to 57 seem like weird homebrew - there must be a good python library for dealing with this stuff :)

optlist, args = getopt.getopt(sys.argv[1:], '')

def dbugpr(msg):
    print '#\n# DEBUG:\n#\n' + msg + '\n#######'

def usage():
    print 'usage:\n  % gwf-lint.py collection-directory font-subdirectory\n'

def fatal():
    sys.exit(2)

is_ok = True

def bogus(msg):
    sys.stdout.write (msg + '\n')

def err(msg):
    global is_ok
    bogus (msg)
    is_ok = False

def errout(msg):
    err(msg)
    fatal()

def done():
    if not is_ok:
        errout ('fatal')
    else:
        sys.exit(0)

def done_if_problems(msg):
    if not is_ok:
        err (msg)
        errout ('fatal')

def help():
    print 'no help message yet\n'

if len(args) != 2:
    sys.stdout.write ('bogus arguments.\n')
    usage()
    fatal()

top_directory = os.path.abspath(args[0])

rel_font_dir = args[1]

directory = os.path.abspath(top_directory + '/' + rel_font_dir)

try:
    os.chdir (directory)
except:
    errout ('Unable to change directory to ' + directory + '.\n')

fontdir_files = os.listdir('.')

# Ensure that there is at least one file matching
# the glob *-Regular.ttf
#
regular_ttf_files = filter(re.compile('^.*-Regular.ttf$').search, fontdir_files)
ttf_files = filter(re.compile('^.*.ttf$').search, fontdir_files)

if len(regular_ttf_files) == 0:
    errout ('No files match *-Regular.ttf!')

# Is there a METADATA file?
#
# If not, we're pretty much stuck for now.
#
if not 'METADATA' in fontdir_files:
    errout ('There\'s no METADATA file!')

#    TODODC 2009-03-23 If there isn't one, make one by 
#        inspecting the regular font, and ask the user for other details

# It's also important that we can read
# and parse the keyword value pairs
# in the damn METADATA file :-)
#

# Parse the METADATA file
#
# This is a little bit involved because the "keywords" in
# METADATA really form a tree of values.  So you might
# have:
#
#    license: Apache2
#
# but you might also have:
#
#
#    description: <p>English description</p>
#    description.ar: <p>[....]</p>
#    description.ru: <p>[....]</p>
#    font.Familyname-SubfamilyExtraLight.ttf.weight: 200
#    font.Familyname-SubfamilyUltraLight.ttf.weight: 200
#
# Figure that as the tree:
# 
#    license: Apache2
#    description: <p>English description</p>
#      ar: <p>[....]</p>
#      ru: <p>[....]</p>
#    font
#      Familyname-SubfamilyUltraLight
#        ttf
#          weight: 200
#      Familyname-SubfamilyExtraLight
#        ttf
#          weight: 200
# 
# Every tree node may thus have no value (like font) 
# or a value (like license and description)
#
# Every node may have named children, or not
# 
# We handle that straightforwardly as follows:
# 
# The global variable meta is a dictionary that maps all
# nodes to their values (as strings) as in:
# 
#         'license' : 'Apache2'
#         'font.Familyname-SubfamilyExtraLight.ttf.weight' : '200'
# 
# The global variable meta_kids is a dictionary that 
# maps all nodes to dictionaries of (names of) their kids:
# 
#       'license' : []
#       'font' : ['Familyname-SubfamilyUltraLight', 
#                'Familyname-SubfamilyExtraLight']
#       'font.Familyname-SubfamilyUltraLight' : ['ttf']
#       'font.Familyname-SubfamilyExtraLight' : ['ttf']
#       'font.Familyname-SubfamilyUltraLight.ttf' : ['weight']
#       'font.Familyname-SubfamilyExtraLight.ttf' : ['weight']
#       'font.Familyname-SubfamilyUltraLight.ttf.weight' : []
#       'font.Familyname-SubfamilyExtraLight.ttf.weight' : []
#
# 

comment_pattern = re.compile('^[ \t]*#')
legit_kw_val = re.compile('^[a-zA-Z.-]+:')

def parse_kwvals(str, src):
    remaining = str + '\n\n'
    chunk = ''
    line_no = 0
    vals = {}
    kids = {}
    key_line_no = {}
    str_is_ok = True

    while remaining != '\n':
        if chunk != '':
            if chunk[-1] == '\\':
                line, remaining = remaining.split('\n', 1)
                chunk = chunk[0:-1] + '\n' + line
                line_no += 1
                continue
            elif legit_kw_val.match (chunk):
                kw, col_val = chunk.split(':', 1)
                val = col_val[1:]
                if kw in vals:
                    str_is_ok = False
                    err (src + ':' + str(line_no) + ': error: repeated key (' + kw +  ')')
                    err (src + ':' + str(key_line_no[kw]) + ': previous definition was here')
                else:
                    vals[kw] = val
                    key_line_no[kw] = line_no
                components = kw.split ('.')
                path = ''
                for component in components:
                    if path == '':
                        path = component
                    else:
                        kids[path] += [component]
                        path = path + '.' + component
                    if not path in kids:
                        kids[path] = []
            elif not comment_pattern.match (chunk):
                str_is_ok = False
                err (src + ':' + str(line_no) + ': error: illegal syntax')
        chunk, remaining = remaining.split('\n', 1)
        line_no += 1

    if not str_is_ok:
        errout ('fatal')

    return [vals, kids, key_line_no]

try:
    metadata = open('METADATA', 'r').read()
except:
    errout ("Unable to read the METADATA file")

meta, meta_kids, meta_key_line_no = parse_kwvals(metadata, 'METADATA')

# We're going to examine various METADATA keywords and values.
#
def missing_mandatory_key(key):
    err ('METADATA:1: error: missing key ' + key)

def has_mandatory_key(key):
    if key in meta:
        return True
    else:
        missing_mandatory_key (key)
        return False

def key_value_problem (key, problem):
    err ('METADATA:' + str(meta_key_line_no[key]) + ': error: (for key ' + key + ') ' + problem)

def illegal_key_value (key):
    key_value_problem (key, 'illegal value')


# For each font directory, there is a checklist
# of things to approve.   Part of what this tool does
# is help you keep track of what is approved and what 
# not approved for each directory, even if you quit 
# work part way through on a given directory and
# restart it later.
# 
# So, we have a meta-meta-data file, so to speak, that
# aims to keep track of the status of the font directory
# vs. the checklist.
# 
# Every checklist item has a name (used as keyword)
# and a value (either "yes" or "no").
# 
# We keep a canonical list of kw items in a sensible order:
# 
# DAVETODO this is a "maintenance point" to pay 
# attention to when tweaking the script.
# 
# Note that these kws don't *exactly* correspond to
# to METADATA keywords.   Some of them do but in 
# general they are just names for the various checks
# you want this script to run.
# 

checklist_kws = ['license',
                 'visibility',
                 'payment',
                 'designer',
                 'url',
                 'category',
                 'subsets',
                 'family',
                 'description',
                 'approved',
                 'weight']

# initialize the checklist to all "no".
# We'll update this after reading the saved copy.
# 

checklist = {}
for kw in checklist_kws:
    checklist[kw] = "no"

# The checklist is "weakly" persistent.  By which I mean
# it is persistent but if this script crashes or 
# something, we try to make sure that that the checklist
# doesn't have any false "yes" answers, even if that
# means having to clean up by hand and redo a 
# particular directory.   Mostly it should just work
# and when it doesn't, fail safe.   The code is a little bit
# fast and loose here with things like file name manipulation
# so...  caution.   Perfection is not possible in this
# domain.  We try to maximize good and minimize harm :-)
# 
# So, let's see if there is already a checklist file
# for this font directory:
#

checklist_dir = os.path.abspath (top_directory + '/LINT-DATA/')

if not os.path.exists (checklist_dir):
    # let's go ahead and create the checklist dir
    #
    err (checklist_dir + ' doesnt exist,')
    os.mkdir (checklist_dir)
    err (checklist_dir + ' now exists.')

checklist_file = os.path.abspath (top_directory + '/LINT-DATA/' + rel_font_dir + '.checklist')

if not os.path.exists (checklist_file):
    err (checklist_file + ' doesnt exist,')
    # let's go ahead and create the checklist file.
    #
    f = open (checklist_file, 'w')
    for x in checklist:
        f.write (x + ': no\n')
    f.close()
    err (checklist_file + ' now exists.')

# The checklist file presumably exists now, either because
# it did when we started or because we just created it.
# Either way, let's examine it:

try:
    checklist_contents = open(checklist_file, 'r').read()
except:
    errout ('Unable to read the checklist file (' + checklist_file + ')')

checklist_file_map, checklist_file_ids, checklist_file_key_line_no = parse_kwvals(checklist_contents, checklist_file)

# Paranoiaclly look for anything in the checklist file
# that is not a recognized checklist item.
# 
for x in checklist_file_map:
    if (not x in checklist):
        err ('unrecognized keyword in checklist file (' + x + ' in ' + checklist_file + ')')
    elif (not checklist_file_map[x] in ['yes', 'no']):
        err ('unrecognized keyword value in checklist file (' + x + 'has value ' + checklist_file_map[x] + ' in ' + checklist_file + ')')
    else:
        checklist[x] = checklist_file_map[x]

done_if_problems('Giving up after failure to read checklist file successfully.')

# This is how we write the checklist file back out:
# 
def checkpoint_checklist ():
    tmp = checklist_file + '.,,,'
    back = checklist_file + '.~'
    if os.path.exists(tmp):
        os.remove (tmp)
    f = open (tmp, 'w')
    for x in checklist:
        f.write (x + ': ' + checklist[x] + '\n')
    f.close ()
    if os.path.exists(back):
        os.remove (back)
    os.rename (checklist_file, back)
    os.rename (tmp, checklist_file)


# As we go through the checklist, there are two actions for each item:
# We automatically check as best as we can (which is in some cases
# is necessarily less than perfect) AND Dave gives a thumbs up or
# thumbs down by "manual inspection" assisted by this script.
# 
# We do the automated checks on every pass, yielding a "yes, no, maybe".
# 
# If Dave has never said "yes" for a given pass, then we ask Dave.
# The default is "yes" if the automatic check looks good and "no"
# otherwise.
# 
# If the automatic check looks good, and Dave has already said "yes" ..
# just move on.
# 
# If the automatic check looks bad, and Dave has already said "yes" ..
# ask again but with a "yes" default.
# 
# When interactive (all that's implement for now), instead of "yes" 
# of "no" Dave can say "quit" and come back later, hopefully without
# losing state.
# 
#

checklist_auto = {}

def begin_checklist_item(item):
    print 'checking "' + item + '"'

def auto_fail_checklist_item(item, msg):
    checklist_auto[item] = 'no'
    print 'Checklist item "' + item + '" doesn\'t look right.  ' + msg

def auto_win_checklist_item(item, msg = ''):
    if item in checklist_auto:
        errout ('some bug trying to win a losing checklist item.  oops.')
    checklist_auto[item] = 'yes'
    print 'Checklist item "' + item +  '" looks ok!  ' + msg

def preserve_checklist_status(item):
    if item in checklist_auto:
        errout ('some bug trying to preserve a settled checklist item.  dang.')
    checklist_auto[item] = checklist[item]

def maybe_preserve_checklist_status(item):
    if not (item in checklist_auto):
        checklist_auto[item] = checklist[item]

def maybe_auto_win_checklist_item(item, msg=''):
    if not item in checklist_auto:
        auto_win_checklist_item (item, msg)


def read_with_default(prompt, default):
    raw = raw_input (prompt + ' [' + default + '] ').strip()
    return raw if (len(raw) != 0) else default

def checklist_ask(item, msg = False):
    if not ((checklist_auto[item] == 'yes') and (checklist[item] == 'yes')):
        the_default = checklist_auto[item]
        while True:
            if msg:
                print msg
            answer = read_with_default ('ok with ' + item + '? (yes / no / quit)', the_default)
            if answer in ['no', 'yes']:
                checklist[item] = answer
                checkpoint_checklist ()
                break
            elif answer == 'quit':
                checkpoint_checklist ()
                done()
            else:
                bogus ('answer no, yes, or quit, please')

# We're going to need to examine various ttf files.
# 
# This simply memoizes loading up those files:
# 
ttf_objs = {}
def font_obj_for (file):
    if not file in ttf_objs:
        ttf_objs[file] = ttLib.TTFont (file)
    return ttf_objs[file]


# Check the license 
#
# This is, um, a likely point of annoying bugs at first.
# It's just too fuzzy what exactly is supposed to go on here
# but here's a start.
#
# 
begin_checklist_item ('license')


blank_lines_pattern = re.compile ('^[ \t]*\n', re.MULTILINE)

if has_mandatory_key ('license'):
    license = meta['license']
    if not license in ['Apache2', 'OFL']:
        illegal_key_value ('license')
    elif license == 'Apache2':
        license_ok = False
        # To check an Apache license we must see that
        # the LICENSE.txt file exists, that the contents
        # are what we expect, and that every TTF
        # has "the canonical apache license URL
        # in the licenseURL key in the NAME table".
        #
        # This check is decidedly non-anal.  For example, it doesn't 
        # ensure that there is a license URL for every platform id,
        # only that there is at least one and that it looks right.
        # 
        if not os.path.exists ('LICENSE.txt'):
            auto_fail_checklist_item ('license', 'The license file "LICENSE.txt" is missing!')
        else:
            try:
                f = open ('LICENSE.txt', 'r')
                ltxt_contents = f.read ()
                f.close ()
                f = open(top_directory + '/LINT-DATA/LICENSE.txt')
                canonical_license = f.read ()
                f.close ()
            except:
                errout ('some damn issue reading LICENSE.txt somewhere')

            if ltxt_contents != canonical_license:
                auto_fail_checklist_item ('license', 'LICENSE.txt doesn\'t match the canonical copy.')
            else:
                for ttf in ttf_files:
                    font = font_obj_for (ttf)
                    found_one = False
                    for x in font['name'].names:
                        # Magically, we know that nameID 14 is where we expect there to be
                        # a license URL.  We muddle through here on encoding issues.
                        #
                        # TOMTODO: http://www.microsoft.com/typography/otspec/name.htm
                        if x.nameID == 14:
                            found_one = True
                            if x.platEncID == 0:
                                file_url = x.string
                            elif x.platEncID == 1:
                                file_url = unicode(x.string, 'utf_16_be')
                            else:
                                errout ('totally confused by license url encoding for file ' + ttf + '  ....  sorry')
                            print 'license URL for ' + ttf +  ' is ' + file_url
                            if file_url != 'http://www.apache.org/licenses/LICENSE-2.0':
                                print 'wtf ' + str(x.string == 'http://www.apache.org/licenses/LICENSE-2.0')
                                auto_fail_checklist_item ('license', 'The URL for font file ' + ttf +  ' looks bogus! (' + x.string + ').')
                    if not found_one:
                        auto_fail_checklist_item ('license' 'No URL found for font file ' + ttf +  ' !')
                maybe_auto_win_checklist_item ('license', 'Checked the license URLs in font files.')
    else:
        # To check an OFL license is just plain messier
        # because formatting isn't consistent and ... well, 
        # blah.   This really calls for an eyeball check.
        # 
        try:
            f = open('OFL.txt', 'r')
            recorded_ofl = f.read()
            f.close ()
        except:
            errout ('some damn issue reading OFL.txt from ' + diretory)

        top_of_ofl = blank_lines_pattern.sub('', recorded_ofl.split('PREAMBLE', 1)[0].replace('\r\n', '\n'))

        print '\n=============================================\n'
        print 'THIS IS THE TOP OF OFL.txt IN THE FONT DIRECTORY:'
        print '\n=============================================\n'
        print top_of_ofl
        print '\n=============================================\n'
        print 'HERE ARE THE FIRST FEW LINES FROM THE TTF FILES:'
        print '\n=============================================\n'
        print '\n'
        for ttf in ttf_files:
            font = font_obj_for (ttf)
            found_one = False
            for x in font['name'].names:
                # Magically, we know that nameID 13 is where we expect there to be
                # a license description.  We again muddle through here on encoding issues.
                #
                # This code is not anal about making sure there is license info
                # for all platforms.  (Have I mentioned what confused pile of crap 
                # TTF has evolved into?  No?  Well, now is a good time to mention it,
                # perhaps.)
                # 
                if x.nameID == 13:
                    found_one = True
                    if x.platEncID == 0:
                        license_desc = x.string
                    elif x.platEncID == 1:
                        license_desc = unicode(x.string, 'utf_16_be')
                    else:
                        errout ('totally confused by license description encoding for file ' + ttf + '  ....  sorry')
                    print ttf + ':\n' + license_desc.split('PREAMBLE')[0] + '\n'
            if not found_one:
                auto_fail_checklist_item ('license' 'No URL found for font file ' + ttf +  ' !')
    maybe_preserve_checklist_status ('license')
    checklist_ask ('license')

# Check the visibility
#
# This is remarkably simpler than checking the license foo.
# 
begin_checklist_item ('visibility')

if not has_mandatory_key ('visibility'):
    auto_fail_checklist_item ('visibility', 'no visibility key?')
else:
    if not meta['visibility'] in ['SANDBOX', 'INTERNAL']:
        illegal_key_value ('visibility')
        auto_fail_checklist_item ('visibility', '"' + meta['visibility'] + '"')
    else:
        auto_win_checklist_item ('visibility', meta['visibility'])

checklist_ask ('visibility')

# Check the payment
#
# Another simple one:
# 

begin_checklist_item ('payment')

if not has_mandatory_key ('payment'):
    auto_fail_checklist_item ('payment', 'no payment key?')
else:
    if not meta['payment'] in ['POOL', 'DESIGNER', 'NONE']:
        illegal_key_value ('payment')
        auto_fail_checklist_item ('payment', '"' + meta['payment'] + '"')
    else:
        auto_win_checklist_item ('payment', meta['payment'])

checklist_ask ('payment')


# Check the designer
#
if has_mandatory_key ('designer'):
    print 'FIXME -- designer checking!'
    # TOMTODO:  it's in googlefontdirectory/designers/
    # 


# Check the url
# 
# DAVETODO you need to be more specific about valid URL checking
#
# I made a pure guess here.   My pure guess is that the URL must
# have a valid scheme and that the scheme must be
# either http or https
# 
# The string "N/A" is in and of itself a valid url but, of course,
# lacks a scheme and is a relative rathr than absolute 
# URL
#
# TOMTODO: make sure domain name with no path and no HTTPS
#


begin_checklist_item ('url')

if not has_mandatory_key ('url'):
    auto_fail_checklist_item ('url', 'Geeze, no URL?  Beginner\'s error!  No Excuses!')
elif not ((meta['url'] == 'N/A') or (urlparse.urlparse(meta['url']).scheme in ['http', 'https'])):
    key_value_problem ('url', 'url value is neither N/A or an http or https URL')
    auto_fail_checklist_item ('url', '"' + meta['url'] + '"')
else:
    auto_win_checklist_item ('url', meta['url'])

checklist_ask ('url')
    
# Check the category
# 
# Another easy one.
# 
begin_checklist_item ('category')

if not has_mandatory_key ('category'):
    auto_fail_checklist_item ('category', 'no category key?')
else:
    if not meta['category'] in ['serif', 'sans-serif', 'display', 'handwriting']:
        illegal_key_value ('category')
        auto_fail_checklist_item ('category', '"' + meta['category'] + '"')
    else:
        auto_win_checklist_item ('category', meta['category'])

checklist_ask ('category')


# Let's have a look at the allowed subsets item, then,
# shall we?
# 
# This is pretty straight forward.  The only variation here is 
# that insted of a single-valued keyword whose value comes from
# a controlled vocabulary, it's a multi-valued keyword whose values
# come from a controlled vocabulary.
# 
# Oh, yeah:
# DAVETODO:  this list of subsets is, I'm certain, in need of 
# of being replaced by the, er, um, actual list.
# 

begin_checklist_item ('category')

allowed_subset_items = ['menu',
                        'latin',
                        'arabic',
                        'cyrillic',
                        'greek',
                        'hebrew',
                        'hindi',
                        'khmer',
                        'korean',
                        'lao',
                        'osmanya',
                        'tamil',
                        'tibetan']


if not has_mandatory_key ('subsets'):
    auto_fail_checklist_item ('subsets', 'no subsets key?')
else:
    subsets = [value.strip() for value in meta['subsets'].split(',')]
    if not (('menu' in subsets)  and ('latin' in subsets)):
        key_value_problem ('subsets', 'does not contain "menu, latin"')
        auto_fail_checklist_item ('subsets', 'missing some essentials, there')
    odd_subsets = [x for x in subsets if not x in allowed_subset_items]
    if odd_subsets != []:
        key_value_problem ('subsets', 'contains unrecognized subsets: ' + str(odd_subsets))
        auto_fail_checklist_item ('subsets', 'some unrecognized subsets, there')
    maybe_auto_win_checklist_item ('subsets', 'no obvious problems with the subsets')
    
checklist_ask ('subsets')

# Check the family
# 
# DAVETODO:  this blows off any attempt to handle font families
# in other than english.  Where can I find a list of name table
# language IDs as they map to the codes used in METADATA?  And,
# is it desirable to do that?
# 
# DAVETODO: the check specified in the davelint pseudocode
# appears to ignore subfamily differences and thus raises flags
# over, for example, the droid fonts?   Easy enough to fix, I think,
# but I left it as specified for now.
# 
begin_checklist_item ('family')

metadata_family = meta['family'] if has_mandatory_key ('family') else ''
ttf_family = ''

if metadata_family == '':
    auto_fail_checklist_item ('family', 'no family name found in METADATA')

for ttf in ttf_files:
    font = font_obj_for (ttf)
    for x in font['name'].names:
        # Magic number: the font family is nameID 1
        # 
        # More encoding mudling here but, really, we should
        # probably also be handling different languageIDs?
        # See DAVETODO above.
        # 
        if x.nameID == 1:
            if x.platEncID == 0:
                this_family = x.string
            elif x.platEncID == 1:
                this_family = unicode(x.string, 'utf_16_be')
            else:
                errout('confused by the family encoding for file ' + ttf)
            print 'font family for ' + ttf + ' is ' + this_family
            ttf_family = this_family if ttf_family == '' else ttf_family
            metadata_family = this_family if metadata_family == '' else metadata_family
            if this_family != ttf_family:
                auto_fail_checklist_item ('family', 'inconsistent font family in ttf files')
            if this_family != metadata_family:
                auto_fail_checklist_item ('family', 'font family in ttf file does not match METADATA')

maybe_auto_win_checklist_item ('family', 'no obvious problem with family declarations')

checklist_ask ('family')

# Check the description
# 
# DAVETODO: Schema for the description check?
#    TOMTODO: schema p, a, em, strong, ol, ul, li   multiple paragraphs
#
# 
# For now, this is just a "by eye" check.
# 
# DAVETODO, TOMTODO: sub-descriptions  what with?
# 
# 

begin_checklist_item ('description')

if not has_mandatory_key ('description'):
    auto_fail_checklist_item ('description', 'no description found in METADATA')
else:
    print '\n=============================================\n'
    print 'THIS IS THE description FROM METADATA:'
    print '\n=============================================\n'
    print meta['description']
    print
    auto_fail_checklist_item ('description', 'no problem noticed, just erring on the side of caution')
    

checklist_ask ('description')

# Check the approved
# 
# Easy enough.  It's either approved or it ain't.
#

begin_checklist_item ('approved')

if not has_mandatory_key ('approved'):
    auto_fail_checklist_item ('approved', 'no approved key?')
else:
    if not meta['approved'] in ['false', 'true']:
        illegal_key_value ('approved')
        auto_fail_checklist_item ('approved', '"' + meta['approved'] + '"')
    else:
        auto_win_checklist_item ('approved', meta['approved'])

checklist_ask ('approved')

# Check the weight and style
#
# DAVETODO: bug Tom to add code to check that there are no
# font.* declarations in METADATA for missing ttf files.
#
# DAVETODO: Unclear which part of the ttf the comparison
# is supposed to be against (for weight)
#

begin_checklist_item ('weight')

checked_weight_for_ttf = {}

for ttf in ttf_files:
    key = 'font.' + ttf + '.weight'
    if not has_mandatory_key (key):
        auto_fail_checklist_item ('weight', 'missing METADATA weight for ' + ttf)
    else:
        metadata_weight = meta[key]
        print 'Weight for ' + ttf + ' in METATADATA is ' + metadata_weight
        font = font_obj_for (ttf)
        found_one = False
        for x in font['name'].names:
            # PROBLEM HUSTON:  
            # 
            # OS/2 table
            # 
            # http://www.microsoft.com/typography/otspec/os2.htm
            # 
            # both numeric and symbolic versions
            # 
            if x.nameID == 2:
                if x.platEncID == 0:
                    this_weight = x.string
                elif x.platEncID == 1:
                    this_weight = unicode(x.string, 'utf_16_be')
                else:
                    errout('confused by the weight encoding for file ' + ttf)
                found_one = True
                if this_weight != metadata_weight:
                    auto_fail_checklist_item ('weight', 'METADATA says ' + metadata_weight + ' but ttf file says ' + this_weight)
        if not found_one:
            auto_fail_checklist_item ('weight', 'no weight found in ttf file')

maybe_auto_win_checklist_item ('weight')

checklist_ask ('weight')


print 'FIXME -- weight checking!'
print 'FIXME -- style checking!'

print 'TODO:'
print ' various DAVETODO items in the source'
print ' menu character set vs. font family name'
print ' menu file checking'
print ' compilability checking'
print ' run fontlnit / fontaine'

errout ('gasp!')
