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
    forall loc in tree(k=k) {
      writeln(here.id, ' -> ', loc.id);
    }
  }

  // Test comm counts
  forall loc in tree(k=k) {
    commArray[here.id, loc.id] += 1;
  }
  writeln(commArray);
  commArray = 0;

}

/* Compute children range for root in k-tree */
proc children(root, k, size) {
  return (root*k+1..#k)(..size);
}

iter tree(locales=Locales, k=2, rootIdx=0): locale {
  const c = children(rootIdx, k, locales.size-1);
  var sublocales: [0..c.length] locale;
  sublocales = locales[rootIdx];
  sublocales[1..] = locales[c];
  for loc in sublocales {
    if loc.id == rootIdx then yield locales[rootIdx];
    else {
      for child in tree(locales=locales, k=k, rootIdx=loc.id) {
        yield child;
      }
    }
  }
}

iter tree(param tag: iterKind, locales=Locales, k=2, rootIdx=0): locale where tag == iterKind.standalone {
  const zeroed = reshape(locales, {0..#locales.size});
  const c = children(rootIdx, k, locales.size-1);
  var sublocales: [0..c.length] locale;
  sublocales = locales[rootIdx];
  sublocales[1..] = zeroed[c];
  coforall loc in sublocales do on loc {
    if loc.id == rootIdx then yield locales[rootIdx];
    else {
      for child in tree(tag=iterKind.standalone, locales=locales, k=k, rootIdx=loc.id) do on child {
        yield child;
      }
    }
  }
}
