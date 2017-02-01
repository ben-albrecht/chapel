use Reflection;

// Simple test
{
  record Simple {

    proc testFoo() {
      writeln('foo');
    }

    proc testBar() {
      writeln('foo');
    }

  }

  var r = new Simple();

  const num = numMethods(r);
  writeln(num);

  // should get first method
  var name = getMethodName(r, 1);
  writeln(name);

  var x = callMethod(r, 'testFoo');

}


// Generic test -- currently not working
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



