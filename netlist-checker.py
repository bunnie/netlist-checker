# edifToUcf.py
#
# based upon sexpParser.py by Paul McGuire (copyright 2007-2011)
#
# This script takes in an EDIF netlist and extracts all the nodes corresponding
# to a particular reference designator (that of the FPGA) and creates a UCF
# file. It will also assign I/O standards based upon a mapping specified near the top
# of this file. Probably in the future it would be a good idea to break that
# mapping into a separate file that can be included.
#
# Andrew 'bunnie' Huang, copyright 2012, BSD license

"""
BNF reference: http://theory.lcs.mit.edu/~rivest/sexp.txt

<sexp>    	:: <string> | <list>
<string>   	:: <display>? <simple-string> ;
<simple-string>	:: <raw> | <token> | <base-64> | <hexadecimal> | 
		           <quoted-string> ;
<display>  	:: "[" <simple-string> "]" ;
<raw>      	:: <decimal> ":" <bytes> ;
<decimal>  	:: <decimal-digit>+ ;
		-- decimal numbers should have no unnecessary leading zeros
<bytes> 	-- any string of bytes, of the indicated length
<token>    	:: <tokenchar>+ ;
<base-64>  	:: <decimal>? "|" ( <base-64-char> | <whitespace> )* "|" ;
<hexadecimal>   :: "#" ( <hex-digit> | <white-space> )* "#" ;
<quoted-string> :: <decimal>? <quoted-string-body>  
<quoted-string-body> :: "\"" <bytes> "\""
<list>     	:: "(" ( <sexp> | <whitespace> )* ")" ;
<whitespace> 	:: <whitespace-char>* ;
<token-char>  	:: <alpha> | <decimal-digit> | <simple-punc> ;
<alpha>       	:: <upper-case> | <lower-case> | <digit> ;
<lower-case>  	:: "a" | ... | "z" ;
<upper-case>  	:: "A" | ... | "Z" ;
<decimal-digit> :: "0" | ... | "9" ;
<hex-digit>     :: <decimal-digit> | "A" | ... | "F" | "a" | ... | "f" ;
<simple-punc> 	:: "-" | "." | "/" | "_" | ":" | "*" | "+" | "=" ;
<whitespace-char> :: " " | "\t" | "\r" | "\n" ;
<base-64-char> 	:: <alpha> | <decimal-digit> | "+" | "/" | "=" ;
<null>        	:: "" ;
"""

from pyparsing import *
from base64 import b64decode
import pprint
import re
import sys
import datetime

def verifyLen(s,l,t):
    t = t[0]
    if t.len is not None:
        t1len = len(t[1])
        if t1len != t.len:
            raise ParseFatalException(s,l,\
                    "invalid data of length %d, expected %s" % (t1len, t.len))
    return t[1]

# define punctuation literals
LPAR, RPAR, LBRK, RBRK, LBRC, RBRC, VBAR = map(Suppress, "()[]{}|")

decimal = Regex(r'0|[1-9]\d*').setParseAction(lambda t: int(t[0]))
#hexadecimal = ("#" + OneOrMore(Word(hexnums)) + "#")\
#                .setParseAction(lambda t: int("".join(t[1:-1]),16))
bytes = Word(printables)
raw = Group(decimal("len") + Suppress(":") + bytes).setParseAction(verifyLen)
token = Word(alphanums + "-./_:*+=")
#base64_ = Group(Optional(decimal|hexadecimal,default=None)("len") + VBAR 
#    + OneOrMore(Word( alphanums +"+/=" )).setParseAction(lambda t: b64decode("".join(t)))
#    + VBAR).setParseAction(verifyLen)
    
qString = Group(Optional(decimal,default=None)("len") + 
                        dblQuotedString.setParseAction(removeQuotes)).setParseAction(verifyLen)
edifHint = Group(LBRK + OneOrMore(Word(printables)) + RBRK)
smtpin = Regex(r'\&?\d+').setParseAction(lambda t: t[0])
#simpleString = base64_ | raw | decimal | token | hexadecimal | qString | smtpin 

# extended definitions
decimal = Regex(r'-?0|[1-9]\d*').setParseAction(lambda t: int(t[0]))
real = Regex(r"[+-]?\d+\.\d*([eE][+-]?\d+)?").setParseAction(lambda tokens: float(tokens[0]))
token = Word(alphanums + "-./_:*+=!<>")

#simpleString = real | base64_ | raw | smtpin | decimal | token | hexadecimal | qString
# get rid of real, base64_ processing passes to speed up parsing a bit; also eliminate hexadecimal
simpleString = raw | smtpin | decimal | token | qString | edifHint

#display = LBRK + simpleString + RBRK
#string_ = Optional(display) + simpleString

sexp = Forward()
sexpList = Group(LPAR + ZeroOrMore(sexp) + RPAR)
sexp << ( simpleString | sexpList )
    
######### Test data ###########
test1 = """
(edif kovan_dvt1_PrjPcb
  (edifVersion 2 0 0)
  (edifLevel 0)
  (keywordMap
     (keywordLevel 0)
  ))
"""

test2 = """
(
 (Net M_SERVO3
  (Joined    (PortRef &13 (InstanceRef U600))
             (PortRef R7 (InstanceRef U800))
  )
 )
 (Net M_SERVO2
  (Joined    (PortRef &5 (InstanceRef U600))
             (PortRef V9 (InstanceRef U800))
  )
)
)
"""

test3 = """
(                                                 
    (cell Everest_ES8328
      (cellType GENERIC)
      (view netListView
        (viewType NETLIST)
        (interface
          (port (rename &1 "1")   (direction INPUT))
          (port (rename &14 "14") (direction OUTPUT))
          (port (rename &17 "17") (direction INOUT))
        )
      )
    )

 (Net M_SERVO3                                                                                    
  (Joined    (PortRef &13 (InstanceRef U600))                                          
             (PortRef R7 (InstanceRef U800))                                                                           
  )                                                                                                      
 )
                                                                                                               
 (Net (rename M_SERVO2 "M.SERVO2")
  (Joined    (PortRef &5 (InstanceRef U600))  
             (PortRef V9 (InstanceRef U800))                                                            
  )                                                                                                 
)                                                                                                         
)                                       
"""

### code

# just a debug routine to print the nets as read in
def netPrint1(netlist, level):
    for expr in netlist:
        if isinstance(expr, list):
            netPrint1(expr, level+1)
        else:
            print " "*level*2, expr

# this procedure determins if a list has any nested lists inside of it.
# returns true if there are, false if there are no list elements inside the list
def hasLists(input_list):
    for item in input_list:
        if( isinstance(item, list) ):
            return True
    return False

# this procedure recursively descends an interpreted netlist and does 
# rename mappings so as to disambiguate any names for the UCF output
def netRename(netlist, renamed):
    niter = netlist[:]
    for elem in niter:
        if isinstance(elem, list):
            if( hasLists( elem ) ):
                renamed.append(netRename(elem, []))
            else:
                if( elem[0] == 'rename' ):
                    renamed.append( elem[2] ) # use elem[1] to go with renamed, [2] for original
                else:
                    renamed.append(elem)
        else:
            # primitives just get returned as base leaves
            renamed.append(elem)

    return renamed

# this procedure extracts a netlist from a parsed EDIF file
# it preserves the structure of the netlist heirarchically
# the result is a nested list, where the top level lists each
# correspond to a net, and behind each net's list is a variable-length
# list of [port, designator] pairs
def netExtract1(netlist, netPinsList):
    nextID = 0
    nextIDcode = ""
    for expr in netlist:
        if isinstance(expr, list):
            netExtract1(expr, netPinsList)
        else:
            if( nextID == 0 ):
                if( expr == "Net" ):
                    nextID = 1
                    nextIDcode = "Net"
                elif( expr == "PortRef" ):
                    nextID = 1
                    nextIDcode = "PortRef"
                elif( expr == "InstanceRef" ):
                    nextID = 1
                    nextIDcode = "InstanceRef"
                elif( expr == "rename" ):
                    nextID = 1
                    nextIDcode = "rename"
                else:
                    nextID = 0
                continue
            else:
                nextID = 0
                if( nextIDcode == "Net" ):
                    netPinsList.append([expr])
                elif( nextIDcode == "rename" ):
                    netPinsList.append([expr])
                elif( nextIDcode == "PortRef" ):
                    if( len(netPinsList[-1:][0]) > 1 ):
                        netPinsList[-1][1].append([re.sub('&','',expr)])
                    else:
                        netPinsList[-1:][0].append([[re.sub('&','',expr)]])
                elif( nextIDcode == "InstanceRef" ):
                    if( len(netPinsList[-1][1]) > 1):
                        netPinsList[-1:][0][-1][-1].append(expr)
                    else:
                        netPinsList[-1:][0][-1][0].append(expr)


# top function for the above recursive call. Sort of inelegant but meh.
def netExtractTop(netlist):
    netPinsList = []
    netExtract1(netlist, netPinsList)
    return netPinsList

# This function takes in the interpreted netlist, finds all elements corresponding
# to the FPGA's designator, and prints UCF-compatible mappings. It also consults a
# regex list of io standard mappings to create IOSTANDARD entries as well.
def netPrintUCF(netlist, designator):
    usedDesignators = []
    for node in netlist:
        listofpins = node[1]
        extraNets = 0
        printLine = ''
        printStd = ''
        for pins in listofpins:
            if( pins[1] == designator ):
                if( usedDesignators.count( node[0] ) == 0 ):
                    printLine = 'NET \"' + node[0] + '\" LOC = ' + pins[0] + ';'
                    # now match against regex list
                    for tup in iostandardMaps:
                        if( re.search( tup[0], node[0] ) ):
                            printStd =  'NET \"' + node[0] + '\" IOSTANDARD = ' + tup[1] + ';'
                            break # important to break once first is found
                    usedDesignators.append( node[0] )
                else:
                    if( extraNets == 0 ):
                        printLine = printLine + '# '
                        extraNets = 1
                    printLine = printLine + pins[0] + " "
        if( printLine != '' ):
            if( extraNets ):
                printLine = "# " + printLine
                printStd = "# " + printStd
            print printLine
            if( len(printStd) > 0 ):
                print printStd

### Run tests
t = None
#alltests = [ locals()[t] for t in sorted(locals()) if t.startswith("test") ]
#alltests = [ test1 test2 test3 ]
alltests = []  # no tests

for t in alltests:
    print '-'*50
    print t
    try:
        sexpr = sexp.parseString(t, parseAll=True)
        pprint.pprint(sexpr.asList())
    except ParseFatalException, pfe:
        print "Error:", pfe.msg
        print pfe.markInputline('^')
    print

###################################
# code section for netlist analysis
###################################

netDict = {}
def buildNetDict(netlist):
    for expr in netlist:
        if(isinstance(expr, list)):
           if(isinstance(expr[0], basestring)):
               if( expr[0] == "Net" ):
#                   pprint.pprint(expr)
                   netDict[expr[1]] = expr[2];
#                   import pdb; pdb.set_trace()

           buildNetDict(expr)

def findComment(propList):
    for key in propList:
        if key[0] == 'Property' and len(key) == 3:
            if key[1] == 'Comment':
                return key[2][1]
        
compDict = {}
def buildCompDict(netlist):
    for expr in netlist:
        if(isinstance(expr, list)):
           if(isinstance(expr[0], basestring)):
               if( expr[0] == "Instance" ):
#                   import pdb; pdb.set_trace()
                   compDict[expr[1]] = findComment(expr);

           buildCompDict(expr)


def countPinsPerNet(netDict_):
    netPinCount = {}
    for keys in netDict_:
        netSize = len(netDict_[keys]) - 1
        if netSize in netPinCount:
            netPinCount[netSize].append(keys)
        else:
            netPinCount[netSize] = []
            netPinCount[netSize].append(keys)

    for keys in netPinCount:
        netPinCount[keys].sort()

    return netPinCount

def findSimilarNets(netDict_, tol):
    tolerance = float(tol)
    diffNets = {} # differential nets -- bookkeeping dictionary
    similarNets = []
    for key_x in netDict_:
        for key_y in netDict_:
            r = lev.ratio( key_x.lower().strip(), key_y.lower().strip())
            if r > (1-tolerance) and len(key_x)/len(key_y) > (1-tolerance) and len(key_x)/len(key_y) < (1+tolerance):
                base_x = re.sub('[0-9]+','#',key_x)
                base_y = re.sub('[0-9]+','#',key_y)
                if( base_x != base_y ):
                    # first check for potential differential net mismatches
                    if re.match('.*_[NP]$', base_x):
                        diff_x = re.sub('_[NP]$', '', base_x)
                        diff_y = re.sub('_[NP]$', '', base_y)
                        if( diff_x == diff_y ):
                            if diff_x in diffNets:
                                diffNets[diff_x] += 1
                            else:
                                diffNets[diff_x] = 1
                    else: 
                        similarNets.append([key_x, key_y])

    similarNets.sort()

    print "Similarly-named nets found: "
    pprint.pprint(similarNets)
    print "Orphaned differential net syntax found (there is either a lone _P or _N variant of this net): "
    for key in diffNets:
        if (diffNets[key]) % 2 != 0:
            print key

def listNetComps(tgtNet):
    if tgtNet in netDict:
        print "Components attached to net \'" + tgtNet + "\':"
        pinlist = netDict[tgtNet]
        index = 1
        while index < len(pinlist):
            # pin lists are well-formed, so access is safe to hard-code...
            designator = pinlist[index][2][1] 
            index += 1
            print designator + ": " + compDict[designator]
    else:
        print "Selected net \'" + tgtNet + "\' not found in netlist"

### actual code

# we want to assemble data into the following structure:
# net_name : pin_name [pin_name ...]
# based upon the additional criteria of an identifier for the refreence designator

# so as we recurse:
# - we will first hit a "Net" keyword -> next token is net_name
# - we will then search for an InstanceRef keyword -> next token is reference_designator; if match add to net_name
# 
# once we have assembled this list, we will take it and generate UCF-format print output

import Levenshtein as lev

if( not (len(sys.argv) == 2 ) ):
    print "Usage: " + sys.argv[0] + " <edif_filename>"
    sys.exit(0)
filename = sys.argv[1]

if( len(sys.argv) == 4 ):
    ofname = sys.argv[3]
    of = open(ofname, 'w')
    sys.stdout = of

f = open(filename, 'r')
edif = f.read()

sys.stderr.write( "parsing " + filename + " (may take a while for large files)...\n" )
sexpr = sexp.parseString(edif, parseAll=True)
netlist = sexpr.asList()

#pprint.pprint(netlist)

print "processing rename elements..."
renamed = netRename(netlist, [])

## build internal databases
print "building internal databases..."
buildNetDict(renamed)
buildCompDict(renamed)

## pre-process some results
pinCount = countPinsPerNet(netDict)

## interact with users
print "Netlist inspector v0.1"

while True:
    cmd = raw_input( "netlist> " )
    if( len(cmd) == 0 ):
        continue
    if( cmd.lower() == "cnt" ):
        pprint.pprint(pinCount)
        for keys in pinCount:
            print "Number of " + str(keys) + " pin nets: " + str(len(pinCount[keys]))
    elif( cmd.lower() == "q" ):
        sys.exit(0)
    elif( cmd.lower() == "dbg" ):
        import pdb; pdb.set_trace()
    elif( cmd.split()[0].lower() == "drc" ):
        print "single pin nets: "
        if '1' in pinCount:
            pprint.pprint(pinCount[1])
        else:
            print "No single pin nets found"
        if (len(cmd.split()) > 1):
            tolerance = cmd.split()[1]
            if float(tolerance) < 0.0 or float(tolerance) > 1.0:
                print "tolerance argument is out of range, setting to 0.11"
                tolerance = 0.11
        else:
            tolerance = 0.1
        print "Typo candidates: "
        findSimilarNets(netDict, tolerance)
        # insert other checks here
    elif( cmd.lower() == "spn" ):
        print "single pin nets: "
        if '1' in pinCount:
            pprint.pprint(pinCount[1])
        else:
            print "No single pin nets found"
    elif( cmd.split()[0].lower() == "npn" ):
        numnets = cmd.split()[1]
        print "displaying " + str(len(pinCount.get(int(numnets), ""))) + " nets with " + numnets + " pins:"
        pprint.pprint(pinCount.get(int(numnets), "(no nets found)"))
    elif( cmd.split()[0].lower() == "list" ):
        if (len(cmd.split()) > 1):
            tgtNet = cmd.split()[1]
        else:
            print "Not enough arguments, aborting"
            continue
        listNetComps(tgtNet)
    else:
        print "command help: "
        print " npn <n> -- print nets with <n> pins"
        print " spn -- report single pin nets only"
        print " cnt -- count and report pins per net"
        print " drc <0.n> -- drc checks with Levenshtein tolerance of <0.n>. Default is 0.1, range is 0-1, with smaller being stricter; recommended values are 0.1 or 0.11"
        print " list <net> -- list components on net <net>"
        print " q -- quit the program"
        print " dbg -- break into the debugger"

#### end of code
