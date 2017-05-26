use Reflection;

record R {
  var x = 10;
  proc foo() { writeln('foo called'); }
  proc bar() { writeln('bar called'); }
}

record Rgs {
  var x = 10;
  proc foo(x) { writeln('foo called'); }
  proc bar(x) { writeln('bar called'); }
}

var r = new R();

for param i in 1..numMethods(r.type) {
  param mName= getMethodName(r.type, i);
  writeln(mName);
  callMethod(r, mName);
}

var args = new Rgs;

for param i in 1..numMethods(args.type) {
  param mName= getMethodName(args.type, i);
  writeln(mName);
  callMethod(args, mName, 3);
}

/* Possible Futures:

record R {
  type t = real;
  proc foo() { writeln('foo called'); }
  proc bar() { writeln('bar called'); }
}

var r = new R();

for param i in 1..numMethods(r.type) {
  param mName= getMethodName(r.type, i);
  writeln(mName);
  callMethod(r, mName);
}

...

proc int.foo() { writeln('foo called'); }

for param i in 1..numMethods(int) {
  param mName= getMethodName(int, i);
  writeln(mName);
  callMethod(r, mName);
}

 */
