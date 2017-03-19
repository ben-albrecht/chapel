use ReferenceCounting;

class Impl {
  var field: int;
  proc init(arg:int) {
    field = arg;
    writeln("in Impl.init");
  }

  proc ~Impl() {
    writeln("in Impl.~Impl");
  }

  proc foo() {
    writeln("in Impl.foo()");
  }
}

proc run() {
  var x = new RefCounted(new Impl(1));
  //x.field = 34;
  writeln(x.field);
}

run();
