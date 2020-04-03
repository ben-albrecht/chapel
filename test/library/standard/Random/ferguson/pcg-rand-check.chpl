use Random;

config const verbose = false;

var seed = 42;
// These are generated by the C version with seed 42 an seq 1
var expect32_1 = [0x4df1ccf9, 0xe5838752, 0x58ed9e10,
                  0xf3e37b51, 0xe7664374, 0x6afde4a8];
// These are generated by the C version with seed 42 an seq 2
var expect32_2 = [0xff85ecc9, 0x4de4d2f6, 0x72eb3394,
                  0x16ee6127, 0x1586aad8, 0xb055098a];


writeln("Checking 32-bit RNG seq 1");
{
  var rs = createRandomStream(seed = seed, parSafe=false,
                            eltType = uint(32), algorithm=RNG.PCG);
  for e32 in expect32_1 {
    //writef("%xu\n", rs.RandomStreamPrivate_rng_states(1));
    var got = rs.getNext();
    if verbose then writef("%xu\n", got);
    assert( got == e32 );
  }

  rs.skipToNth(1);

  for e32 in expect32_1 {
    //writef("%xu\n", rs.RandomStreamPrivate_rng_states(1));
    var got = rs.getNext();

    if verbose then writef("%xu\n", got);
    assert( got == e32 );
  }

  for (i, e32) in zip(1..6, expect32_1) {
    var got = rs.getNth(i);

    if verbose then writef("%xu\n", got);
    assert( got == e32 );
  }
}

{
  var rs = createRandomStream(seed = seed, parSafe=false,
                            eltType = int(32), algorithm=RNG.PCG);
  for e32 in expect32_1 {
    //writef("%xu\n", rs.RandomStreamPrivate_rng_states(1));
    var got = rs.getNext();
    if verbose then writef("%xu\n", got);
    assert( got:uint(32) == e32 );
  }

  rs.skipToNth(1);

  for e32 in expect32_1 {
    //writef("%xu\n", rs.RandomStreamPrivate_rng_states(1));
    var got = rs.getNext();
    if verbose then writef("%xu\n", got);
    assert( got:uint(32) == e32 );
  }

  for (i, e32) in zip(1..6, expect32_1) {
    var got = rs.getNth(i);
    if verbose then writef("%xu\n", got);
    assert( got:uint(32) == e32 );
  }
}


// check 8 bit version
{
  var rs = createRandomStream(seed = seed, parSafe=false,
                            eltType = uint(8), algorithm=RNG.PCG);
  for e32 in expect32_1 {
    //writef("%xu\n", rs.RandomStreamPrivate_rng_states(1));
    var got = rs.getNext();

    if verbose then writef("%xu\n", got);
    assert( got == e32 >> 24 );
  }

  rs.skipToNth(1);

  for e32 in expect32_1 {
    //writef("%xu\n", rs.RandomStreamPrivate_rng_states(1));
    var got = rs.getNext();

    if verbose then writef("%xu\n", got);
    assert( got == e32 >> 24 );
  }

  for (i, e32) in zip(1..6, expect32_1) {
    var got = rs.getNth(i);

    if verbose then writef("%xu\n", got);
    assert( got == e32 >> 24 );
  }
}

// check 16 bit version
{
  var rs = createRandomStream(seed = seed, parSafe=false,
                            eltType = uint(16), algorithm=RNG.PCG);

  for e32 in expect32_1 {
    //writef("%xu\n", rs.RandomStreamPrivate_rng_states(1));
    var got = rs.getNext();

    if verbose then writef("%xu\n", got);
    assert( got == e32 >> 16 );
  }

  rs.skipToNth(1);

  for e32 in expect32_1 {
    //writef("%xu\n", rs.RandomStreamPrivate_rng_states(1));
    var got = rs.getNext();

    if verbose then writef("%xu\n", got);
    assert( got == e32 >> 16 );
  }

  for (i, e32) in zip(1..6, expect32_1) {
    var got = rs.getNth(i);

    if verbose then writef("%xu\n", got);
    assert( got == e32 >> 16 );
  }
}

writeln("Checking 2x 32-bit RNG seq 1 seq 2");

// check 64 bit version
{
  var rs = createRandomStream(seed = seed, parSafe=false,
                            eltType = uint(64), algorithm=RNG.PCG);
  for (e32_1, e32_2) in zip(expect32_1, expect32_2) {
    //writef("%xu\n", rs.RandomStreamPrivate_rng_states(1));
    var got = rs.getNext();

    if verbose then writef("%xu\n", got);
    assert( got == (e32_1:uint(64) << 32) | e32_2:uint(64) );
  }

  rs.skipToNth(1);

  for (e32_1, e32_2) in zip(expect32_1, expect32_2) {
    //writef("%xu\n", rs.RandomStreamPrivate_rng_states(1));
    var got = rs.getNext();

    if verbose then writef("%xu\n", got);
    assert( got == (e32_1:uint(64) << 32) | e32_2:uint(64) );
  }

  for (i, e32_1, e32_2) in zip(1..6, expect32_1, expect32_2) {
    var got = rs.getNth(i);

    if verbose then writef("%xu\n", got);
    assert( got == (e32_1:uint(64) << 32) | e32_2:uint(64) );
  }
}

//writeln("Checking real(32)");
// check that real(32) reproduces
// TODO - bug in resolution?
/*{
  var expect:[1..6] real(32);

  fillRandom(expect, seed=seed, algorithm=RNG.PCG);

  var rs = createRandomStream(seed = seed, eltType = real(32), algorithm=RNG.PCG);

  for i in 1..6 {
    //writef("%xu\n", rs.RandomStreamPrivate_rng_states(1));
    var got = rs.getNext();

    if verbose then writef("%n\n", got);
    assert( got == expect[i] );
  }

  rs.skipToNth(1);

  for i in 1..6 {
    //writef("%xu\n", rs.RandomStreamPrivate_rng_states(1));
    var got = rs.getNext();

    if verbose then writef("%n\n", got);
    assert( got == expect[i] );
  }

  for i in 1..6 {
    var got = rs.getNth(i);

    if verbose then writef("%n\n", got);
    assert( got == expect[i] );
  }
}*/

writeln("Checking real(64)");
// check that real(64) reproduces
{
  var expect:[1..6] real(64);

  fillRandom(expect, seed=seed, algorithm=RNG.PCG);

  var rs = new owned RandomStream(seed = seed, eltType = real(64));

  for i in 1..6 {
    //writef("%xu\n", rs.RandomStreamPrivate_rng_states(1));
    var got = rs.getNext();

    if verbose then writef("%n\n", got);
    assert( got == expect[i] );
  }

  rs.skipToNth(1);

  for i in 1..6 {
    //writef("%xu\n", rs.RandomStreamPrivate_rng_states(1));
    var got = rs.getNext();

    if verbose then writef("%n\n", got);
    assert( got == expect[i] );
  }

  for i in 1..6 {
    var got = rs.getNth(i);

    if verbose then writef("%n\n", got);
    assert( got == expect[i] );
  }
}

writeln("Checking random shuffle and permutation");
// try a random permutation
{
  for i in 1..10 {
    var arr = [10,20,30,40];

    shuffle(arr, seed=i, algorithm=RNG.PCG);
    writeln(arr);
  }

  for i in 1..10 {
    var arr:[1..4] int;

    permutation(arr, seed=i, algorithm=RNG.PCG);
    writeln(arr);
  }
}


writeln("Checking 8-bit once-only RNG");
{
    var two_n = 256;

    for seed in 0..10 {
      for stream in 1..10 {
        var inc = pcg_getvalid_inc(stream:uint):uint(8);
        var hits:[0..#two_n] int;
        var rng = new pcg_setseq_8_rxs_m_xs_8_rng();

        rng.srandom(seed:uint(8), inc);

        for i in 0..#two_n {
          var got = rng.random(inc);
          if verbose then
            writeln(got, " i=", i, " n=", 8, " seed=", seed, " stream=", stream);
          hits[got] += 1;
        }

        if verbose then
          writeln();

        for i in 0..#two_n {
          assert(hits[i] == 1);
        }
      }
    }
}

writeln("Checking generalized once-only RNG");
{
  for n in 1..20 {
    var two_n:uint = 1:uint << n;

    for seed in 0..2 {
      for stream in 1..2 {
        var inc = pcg_getvalid_inc(stream:uint);
        var hits:[0:uint..#two_n] int;
        var rng = new pcg_setseq_N_rxs_m_xs_N_rng(n);

        rng.srandom(seed:uint, inc);

        for i in 0..#two_n {
          var got = rng.random(inc);

          if verbose then
            writeln(got, " i=", i, " n=", n, " seed=", seed, " stream=", stream);

          hits[got] += 1;
        }

        if verbose then
          writeln();

        for i in 0:uint..#two_n {
          assert(hits[i] == 1);
        }
      }
    }
  }
}
