use Reflection;

// Simple test
{
  record Simple {

    proc testFoo() {
      writeln('foo');
    }

    proc testBar() {
      writeln('bar');
    }

  }

  var r = new Simple();

  param num = numMethods(r.type);
  writeln(num);

  // should get first method
  for param i in 1..num {
    param name = getMethodName(r.type, i);
    writeln(name);
    callMethod(r, name);
  }

}


// Generic test -- currently not working
/*
{
  record Generic {

    var x;

    proc Generic(x) {
      this.x = x;
    }

    proc testFoo() {
      writeln('foo');
    }

  }

  var r = new Generic(1);

  const num = numMethods(r);
  writeln(num); // should be same as num before..

}

*/


