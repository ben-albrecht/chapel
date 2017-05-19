use Reflection;

record R {
  var x = 10;
  proc foo() { writeln('foo called'); }
  proc bar() { writeln('bar called'); }
}

var r = new R();

writeln(numMethods(r.type));
// Slightly different kind of test..
for param i in 1..numMethods(r.type) {
  param mName= getMethodName(r.type, i);
  writeln(mName);
  callMethod(r, mName);
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
