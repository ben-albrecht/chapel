use BlockDist;

config const k = 2;

const commLocDom = {0..#numLocales, 0..#numLocales};
var localesArray : [commLocDom] locale;
for loc in Locales do localesArray[loc.id, ..] = loc;

const commDom = commLocDom dmapped Block(boundingBox=commLocDom, targetLocales=localesArray);
var commArray: [commDom] int;

proc main() {

  writeln('localeTree');

  // Test order (serialized)
  serial {
    forall loc in localeTree(k=k) {
      writeln(here.id, ' -> ', loc.id);
    }
  }

  // Test comm counts
  forall loc in localeTree(k=k) {
    commArray[here.id, loc.id] += 1;
  }
  writeln(commArray);
  commArray = 0;


  // Broadcast
  writeln('localeTreeTraversal');

  // Test order (serialized)
  serial {
    forall loc in localeTreeTraversal(k=k) {
      writeln(here.id, ' -> ', loc.id);
    }
  }

  // Test comm counts
  forall loc in localeTreeTraversal(k=k) {
    commArray[here.id, loc.id] += 1;
  }
  writeln(commArray);
  commArray = 0;


  // Gather
  writeln('localeTreeTraversalReversed');
  // Test order (serialized)
  serial {
    forall loc in localeTreeTraversalReversed(k=k) {
      writeln(here.id, ' -> ', loc.id);
    }
  }

  // Test comm counts
  forall loc in localeTreeTraversalReversed(k=k) {
    commArray[here.id, loc.id] += 1;
  }
  writeln(commArray);
}


/*
  Compute height of `k`-tree with `size` elements
 */
proc height(k, size) { return ceil(log(size) / log(k)):int; }


/*
   Return range of nodes at height `h` for a `k`-tree with `size` elements
 */
proc nodes(h, k, size) {
  const numNodes = ((k**(h+1) - 1)/(k - 1)) - 1;
  return ((numNodes - k**h + 1)..numNodes)(..size-1);
}


/*
   Return range of nodes under `parent` node for a `k`-tree
   with `size` elements
 */
proc children(parent, k, size) {
  return (parent*k+1..#k)(..size-1);
}


/*
   Return parent node of `child` node `k`-tree
 */
proc parent(child, k) {
  return floor((child - 1)/k): int;
}


// Serial iterator
pragma "no doc"
iter localeTree(k=2, locales=Locales) {
  halt('Serial iterator not supported');
  yield locales[0];
}


/* TODO --
   Needs to be recursive, e.g.

   sublocales = [Locales[root], (..Locales[children(root)])];
   coforall loc in sublocales {
     if loc == root then yield root;
     else {
      forall child in children(loc) do yield child;
     }
   }

   forall loc in LocaleTree() {

   }
 */
/*
  Iterates through `locales` via the  `on parent - yield children` broadcast
  pattern, where each parent locale has `k` children, ultimately yielding every
  locale in `locales`
*/
iter localeTree(param tag:iterKind, k=2, locales=Locales) where tag == iterKind.standalone {
  yield locales[0];
  const size = locales.size;
  for h in 0..#height(k, size) {
    coforall parent in nodes(h, k, size) do on locales[parent] {
      forall child in children(parent, k, size) {
        yield locales[child];
      }
    }
  }
}

// Serial iterator
pragma "no doc"
iter localeTreeTraversal(k=2, locales=Locales) {
  halt('Serial iterator not supported');
  yield locales[0];
}

/*
 Iterates through `locales` via the  `on parent - yield children` pattern,
 where each parent locale has `k` children, ultimately yielding every locale in `locales`,
 except for the `root` locale
 */
iter localeTreeTraversal(param tag:iterKind, k=2, locales=Locales) where tag == iterKind.standalone {
  const size = locales.size;
  for h in 0..#height(k, size) {
    coforall parent in nodes(h, k, size) do on locales[parent] {
      forall child in children(parent, k, size) {
        yield locales[child];
      }
    }
  }
}


// Serial iterator
pragma "no doc"
iter localeTreeTraversalReversed(k=2, locales=Locales) {
  halt('Serial iterator not supported');
  yield locales[0];
}

/*
 Iterates through `locales` via the  `on child - yield parent` pattern,
 where each parent locale has `k` children, ultimately doing an `on-statement` for
 every locale in `locales`, except for the `root` locale
 */
iter localeTreeTraversalReversed(param tag:iterKind, k=2, locales=Locales) where tag == iterKind.standalone {
  const size = locales.size;
  for h in 1..#height(k, size)-1 by -1 {
    coforall child in nodes(h, k, size) do on locales[child] {
      const p = parent(child, k);
      yield locales[p];
    }
  }
}

// TODO -- reindex to ensure 0-based indexing, in case of slicing
/*
 Broadcast `from` locale's copy of elements to every other locale
 using the `localeTreeTraversalReversed` iterator
 */
//proc ReplicatedDist.broadcast(from: locale, locales=Locales, k=2)) { }
