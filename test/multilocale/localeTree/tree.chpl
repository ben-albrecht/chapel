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

iter tree(root=0, locales=Locales, k=2): locale {
  const c = children(root, k, locales.size-1);
  var sublocales: [0..c.length] locale;
  sublocales = locales[root];
  sublocales[1..] = locales[c];
  for loc in sublocales {
    if loc.id == root then yield locales[root];
    else {
      for child in tree(root=loc.id, locales=locales, k=k) {
        yield child;
      }
    }
  }
}

iter tree(param tag: iterKind, root=0, locales=Locales, k=2): locale where tag == iterKind.standalone {
  const c = children(root, k, locales.size-1);
  var sublocales: [0..c.length] locale;
  sublocales = locales[root];
  sublocales[1..] = locales[c];
  coforall loc in sublocales do on loc {
    if loc.id == root then yield locales[root];
    else {
      // Making this a forall -> ):
      //  $CHPL_HOME/modules/internal/ChapelIteratorSupport.chpl:178: error: unable to resolve return type of function '_toStandalone'
      //  tree.chpl:52: In iterator 'tree':
      //  tree.chpl:60: error: called recursively at this point
      for child in tree(root=loc.id, locales=locales, k=k) do on child {
        yield child;
      }
    }
  }
}
