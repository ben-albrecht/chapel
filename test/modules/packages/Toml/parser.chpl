/* 
Parser module with the Node class for the Chapel TOML library.
*/

use reader;
use Regexp;
use DateTime;



// Main method primarily for debugging
proc main(args: [] string) {
  const source = new Source(args[1]);
  const parser = new Parser(source);
  writeln(parser.parseLoop());
  delete parser;
  delete source;
}

// Prints a line by line output of parsing process
config const DEBUG: bool = false;


class Parser {

  var source;
  var D: domain(string);
  var table: [D] Node;
  var rootTable = new Node(table);
  var curTable: string;

  // Regex constants to match Tokens
  const doubleQuotes = '".*?"',
        singleQuotes = "'.*?'",
        digit = "\\d+",
        keys = "^\\w+";
  const Str = compile(doubleQuotes + '|' + singleQuotes),
        kv = compile('|'.join(doubleQuotes, singleQuotes, digit, keys)),
        dt = compile('^\\d{4}-\\d{2}-\\d{2}[ T]\\d{2}:\\d{2}:\\d{2}$'),
        realNum = compile("\\+\\d*\\.\\d+|\\-\\d*\\.\\d+|\\d*\\.\\d+"),
        ints = compile("(\\d+|\\+\\d+|\\-\\d+)"),
        inBrackets = compile("(\\[.*?\\])"),
        brackets = compile('\\[|\\]'),
        whitespace = compile("\\s"),
        comment = compile("(\\#)"),
        comma = compile("(\\,)");

    

  proc parseLoop() : Node {

    while(readLine(source)) {
      var token = top(source);
      
      if token == '#' {
	parseComment();
      }
      else if inBrackets.match(token) {
	parseTable();
      }
      else if brackets.match(token) {
        parseSubTbl();
      }
      else if kv.match(token) {
	parseAssign();
      }
      else {
	halt("Unexpected token ->", getToken(source));
      }
      if DEBUG {
	writeln();
	writeln("========================= Debug Info  ==========================");
	source.debug();
	writeln();
	writeln(rootTable);
	writeln();
        writeln("================================================================");
      }
    }
    return rootTable;
  }

  proc parseTable() {
    var toke = getToken(source);
    var tablename = brackets.sub('', toke);
    var tblD: domain(string);
    var tbl: [tblD] Node;
    if !rootTable.pathExists(tablename) {
      rootTable[tablename] = new Node(tbl);
    }
    curTable = tablename;
  }

  proc parseSubTbl() {
    skipNext(source);
    var tblname = getToken(source);
    skipNext(source);
    var tblD: domain(string);
    var tbl: [tblD] Node;
    var (tblPath, tblLeaf) = splitTblPath(tblname);
    if !rootTable.pathExists(tblPath) then makePath(tblPath);
    rootTable.getIdx(tblPath)[tblLeaf] = new Node(tbl);
    curTable = tblname;
  }

  proc makePath(tblPath: string) {
    var path = tblPath.split('.');
    var firstIn = path.domain.first;
    var first = true;
    var i: int = 0;
    for parent in path {
      if first {
        var tblD: domain(string);
        var tbl: [tblD] Node;
        rootTable[parent] = new Node(tbl);
        first = false;
      }
      else {
        var tblD: domain(string);
        var tbl: [tblD] Node;
        var grandParent = '.'.join(path[..firstIn+i]);
        rootTable.getIdx(grandParent)[parent] = new Node(tbl);
        i+=1;
      }
    }
  }

  proc parseInlineTbl(key: string) {
    var tblname: string;
    var tblD: domain(string);
    var tbl: [tblD] Node;
    if curTable.isEmptyString() {
      tblname = key;
      rootTable[key] = new Node(tbl);
    }
    else {
      tblname = '.'.join(curTable, key);
      var (tblPath, tblLeaf) = splitTblPath(tblname);
      rootTable.getIdx(tblPath)[tblLeaf] = new Node(tbl);
    }
    var temp = curTable;
    curTable = tblname;
    while top(source) != '}' {
      parseAssign();
      if top(source) == ',' {
        skipNext(source);
      }
    }
    skipNext(source);
    curTable = temp; // resets curTable after assignments to inline
  }

  proc parseAssign() {
    var key = getToken(source);
    var equals = getToken(source);
    if top(source) == '{' {
      skipNext(source);
      parseInlineTbl(key);
    }
    else {
      var value = parseValue();
      if curTable.isEmptyString() then rootTable[key] = value;
      else rootTable.getIdx(curTable)[key] = value;
    }
  }
  
  // Skip the line with the comment 
  proc parseComment() {
    skipLine(source);
  }  

  // Returns leaf of embedded table
  proc splitTblPath(s: string) {
    var A = s.split('.');
    var fIdx = A.domain.first;
    var leaf = A[A.domain.last];
    var path = '.'.join(A[..A.domain.last-1]);
    if A.size == 1 then path = A[fIdx];
    return (path, leaf);
  }

  // [servers.alpha.echo] => [servers, alpha, echo]
  proc splitName(s: string) {
    var A = s.split('.');
    return A;
  }
  
  
  proc parseValue(): Node {
    var val = top(source);
    // Array
    if val == '['  {
      skipNext(source);
      var nodeDom: domain(1);
      var array: [nodeDom] Node;
      while top(source) != ']' {
	if comma.match(top(source)) {
	  skipNext(source);
	}
        else if comment.match(top(source)) {
          skipLine(source);
        }
	else {
	  var toParse = parseValue();
	  array.push_back(toParse);
	}
      }
      skipNext(source);
      var nodeArray = new Node(array);
      return nodeArray;
    }
    // Strings (includes multi-line) 
    else if Str.match(val) {
      var toStr: string;
      if val.startsWith('"""') {
        toStr += getToken(source).strip('"""', true, false);
        while toStr.endsWith('"""') == false {
	  toStr += " " + getToken(source);
        }
        var mlStringNode = new Node(toStr.strip('"""'));
        return mlStringNode;
      }
      else if val.startsWith("'''") {
        toStr += getToken(source).strip("'''", true, false);
        while toStr.endsWith("'''") == false {
          toStr += " " + getToken(source);
        }
        var mlStringNode = new Node(toStr.strip("'''"));
        return mlStringNode;
      }
      else {
        toStr = getToken(source).strip('"').strip("'");
	var stringNode = new Node(toStr);
	return stringNode;
      }
    }
    // DateTime
    else if dt.match(val) {
      var date = datetime.strptime(getToken(source), "%Y-%m-%dT%H:%M:%SZ");
      var Datetime = new Node(date);
      return Datetime;
    }
    // Real
    else if realNum.match(val) {
      var token = getToken(source);
      var toReal = token: real;
      var realNode = new Node(toReal);
      return realNode;
    }
    // Int
    else if ints.match(val) {
      var token = getToken(source);
      var toInt = token: int;
      var intNode = new Node(toInt);
      return intNode;
    } 
    // Boolean
    else if val == "true" || val ==  "false" {
      var token = getToken(source);
      var toBool = token: bool;
      var boolNode = new Node(toBool);
      return boolNode;
    }
    else if val == '#' {
      skipLine(source);
      return parseValue();
     }
    // Error
    else {
      halt("Unexpected Token: ", "'", val, "'");
    }
  }
}


/*
 Class to hold various types parsed from input
 Used to recursivly hold tables and respective values
 */
class Node {
  var i: int;
  var boo: bool;
  var re: real;
  var s: string;
  var dt: datetime;
  var dom: domain(1);
  var arr: [dom] Node;
  var D: domain(string);
  var A: [D] Node;
  
  // Tags to identify type
  const fieldBool = 1,
    fieldInt = 2,
    fieldArr = 3,
    fieldNode = 4,
    fieldReal = 5,
    fieldString = 6,
    fieldEmpty = 7,
    fieldDate = 8;
  var tag: int = fieldEmpty;  


  // Empty
  proc init() {
    tag = fieldEmpty;
  }

  // String
  proc init(s:string) {
    this.s = s;
    tag = fieldString;
  }

  // Node
  proc init(A: [?D] Node) where isAssociativeDom(D) {
    this.D = D;
    this.A = A;
    tag = fieldNode;
  }
  // Datetime
  proc init(dt: datetime) {
    this.dt = dt;
    tag = fieldDate;
  }

  // Int
  proc init(i: int) {
    this.i = i;
    tag = fieldInt;
  }

  // Boolean
  proc init(boo: bool) {
    this.boo = boo;
    tag = fieldBool;
  }

  // Real
  proc init(re: real) {
    this.re = re;
    tag = fieldReal;
  }

  // Array
  proc init(arr: [?dom] Node) where isAssociativeDom(dom) == false  {
    this.dom = dom;
    this.arr = arr;
    tag = fieldArr;
  }

  proc this(idx: string) ref {
    return A[idx];
  }

  // Returns the index of the tbl path given as a parameter
  proc getIdx(tbl: string) ref : Node {
    var indx = tbl.split('.');
    var top = indx.domain.first;
    if indx.size < 2 {
      if this.A.domain.member(tbl) == false {
        halt("Error in getIdx '", tbl, "' does not exist");
      }
      else {
        return this.A[tbl];
      }
    } 
    else {
      var next = '.'.join(indx[top+1..]);
      if this.A.domain.member(indx[top]) {
        return this.A[indx[top]].getIdx(next);
      }
      else {
        halt("Error in getIdx2");
      }
    }
  }


  proc pathExists(tblpath: string) : bool {
    var path = tblpath.split('.');
    var top = path.domain.first;
    if path.size < 2 {
      if this.A.domain.member(tblpath) == false {
        return false;
      }
      else {
        return true;
      }
    }
    else {
      var next = '.'.join(path[top+1..]);
      if this.A.domain.member(path[top]) {
        return this.A[path[top]].pathExists(next);
      }
      else {
        return false;
      }
    }
  }
  
  
  proc writeThis(f) {
    var flatDom: domain(string);
    var flat: [flatDom] Node;
    this.flatten(flat);       // Flattens containing Node
    printValues(f, this);     // Prints key values in containing Node
    printHelp(flat, f);       // Prints tables in containg Node
  }

  /*
   Flatten tables into flat associative array for writing
   */
  proc flatten(flat: [?d] Node, rootKey = '') : flat.type { 
    for (k, v) in zip(this.D, this.A) {
      if v.tag == 4 {
        var fullKey = k;
        if rootKey != '' then fullKey = '.'.join(rootKey, k);
        flat[fullKey] = v;
        v.flatten(flat, fullKey);
      }
    }
    return flat;
  }

  proc printHelp(flat: [?d] Node, f:channel) {
    for k in d.sorted() {
      f.writeln('[', k, ']');
      printValues(f, flat[k]);
    }
  }
  
  /*
   Send values from table to toString for writing
   Skip tables
   */
  proc printValues(f: channel, v) {
    for (key, value) in zip(v.D, v.A) {
      select value.tag {
        when 4 do continue; // Table
        when 1 {
          f.writeln(key, ' = ', toString(value));
        }
        when 2 {
          f.writeln(key, ' = ', toString(value));
        }
        when 3 {
          var final: string;
          f.write(key, ' = ');
          final += '[';
          for k in value.arr {
            if value.arr.domain.size == 1 || k == value.arr[value.arr.domain.last] {
              final += toString(k);
            }
            else {
              final += toString(k) + ', ';
            }
          }
          final += ']';
          f.writeln(final);
        }
        when 5 {
          f.writeln(key, ' = ', toString(value));
        }
        when 6 {
          f.writeln(key, ' = ', toString(value));
        }
        when 7 {
          halt("Keys have to have a value");
        }
        when 8 {
          f.writeln(key, ' = ', toString(value));
        }
        otherwise { 
          f.write("not yet supported");
        }
        } 
    }
    f.writeln();
  }
  
  proc toString(val: Node) : string { 
    select val.tag {
      when 1 do return val.boo;
      when 2 do return val.i;
      when 3 {
        var final: string;
        final += '[';
        for k in val.arr {
          if val.arr.domain.size == 1 || k == val.arr[val.arr.domain.last] {
            final += toString(k);
          }
          else {
            final += toString(k) + ', ';
          }
        }
        final += ']';
        return final;
      }
      when 5 do return val.re;
      when 6 do return ('"' + val.s + '"');
      when 7 do return ""; // empty
      when 8 do return val.dt.isoformat();
      otherwise {
        return val;
        writeln("something weird happened with", val);
      }
      }
  }
  
    
  /* Don't forget to free your memory! */
  proc deinit() {
    for a in A {
      delete a;
    }
  }
}
