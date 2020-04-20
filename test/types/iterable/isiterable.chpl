// Some types
youAreNotIterable(bool);
youAreNotIterable(int);
youAreNotIterable(uint);
youAreNotIterable(real);
youAreNotIterable(imag);
youAreNotIterable(complex);
youAreIterable(string);
youAreIterable(domain(1));

// Some values
enum alphabet {A, B, C};
youAreNotIterable(alphabet);

var a = [1,2,3,4];
youAreIterable(a);

var t = (1,2,3,4);
youAreIterable(t);

record R { iter these() { yield 1; } }
youAreIterable(R);

record R2 { }
youAreNotIterable(R2);

// Range
youAreIterable(1..10);


// Associatve array
var d: domain(string);
var aa: [d] int;
youAreIterable(aa);

// Iterable expression
youAreIterable(for i in 1..4 do i*2);

iter f() {
  for i in 2..10 by 2 {
    yield i;
  }
}

youAreIterable(for i in 1..4 do i*2);
youAreIterable(f());


proc youAreNotIterable(type t) {
  var x: t;
  youAreNotIterable(x);
}

proc youAreIterable(type t) {
  var x: t;
  youAreIterable(x);
}

proc youAreNotIterable(x) {
  if isIterable(x) then
    writeln('Assertion failed, this *is* iterable: ', x);
}
proc youAreIterable(x) {
  if !isIterable(x) then
    writeln('Assertion failed, this is *not* iterable: ', x);
}
