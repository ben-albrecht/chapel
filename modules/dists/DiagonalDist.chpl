/*
 * Copyright 2004-2017 Cray Inc.
 * Other additional copyright holders may be indicated within.
 * 
 * The entirety of this work is licensed under the Apache License,
 * Version 2.0 (the "License"); you may not use this file except
 * in compliance with the License.
 * 
 * You may obtain a copy of the License at
 * 
 *     http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

//
// The Diagonal distribution is defined with six classes:
//
//   Diagonal       : distribution class
//   DiagonalDom    : domain class
//   DiagonalArr    : array class
//   LocDiagonal    : local distribution class (per-locale instances)
//   LocDiagonalDom : local domain class (per-locale instances)
//   LocDiagonalArr : local array class (per-locale instances)
//
// When a distribution, domain, or array class instance is created, a
// corresponding local class instance is created on each locale that is
// mapped to by the distribution.
//

//
// TO DO List
//
// 1. ...
//

use DSIUtil;

//
// These flags are used to output debug information and run extra
// checks when using Diagonal.  Should these be promoted so that they can
// be used across all distributions?  This can be done by turning them
// into compiler flags or adding config parameters to the internal
// modules, perhaps called debugDists and checkDists.
//
config param debugDiagonalDist = false;

// TODO diagonal - need this?
//
// If the testFastFollowerOptimization flag is set to true, the
// follower will write output to indicate whether the fast follower is
// used or not.  This is used in regression testing to ensure that the
// 'fast follower' optimization is working.
//
config param testFastFollowerOptimization = false;

//
// Diagonal Distribution Class
//
// rank : generic rank that must match the rank of domains and arrays
//        declared over this distribution
//
// idxType: generic index type that must match the index type of
//          domains and arrays declared over this distribution
//
// boundingBox: a non-distributed domain defining a bounding box used
//              to partition the space of all indices across the array
//              of target locales; the indices inside the bounding box
//              are partitioned "evenly" across the locales and
//              indices outside the bounding box are mapped to the
//              same locale as the nearest index inside the bounding
//              box
//
// targetLocDom: a non-distributed domain over which the array of
//               target locales and the array of local distribution
//               classes are defined
//
// targetLocales: a non-distributed array containing the target
//                locales to which this distribution partitions indices
//                and data
//
// locDist: a non-distributed array of local distribution classes
//

class Diagonal : BaseDist {
  param rank: int;
  type idxType = int;
  var boundingBox: domain(rank, idxType);
  var targetLocDom: domain(rank);
  var targetLocales: [targetLocDom] locale;
  var locDist: [targetLocDom] LocDiagonal(rank, idxType);
  type sparseLayoutType = DefaultDist;
}

//
// Local Diagonal Distribution Class
//
// rank : generic rank that matches Diagonal.rank
// idxType: generic index type that matches Diagonal.idxType
// myChunk: a non-distributed domain that defines this locale's indices
//
class LocDiagonal {
  param rank: int;
  type idxType;
  const myChunk: domain(rank, idxType);
}

//
// Diagonal Domain Class
//
// rank:      generic domain rank
// idxType:   generic domain index type
// stridable: generic domain stridable parameter
// dist:      reference to distribution class
// locDoms:   a non-distributed array of local domain classes
// whole:     a non-distributed domain that defines the domain's indices
//
class DiagonalDom: BaseRectangularDom {
  param rank: int;
  type idxType;
  param stridable: bool;
  type sparseLayoutType;
  const dist: Diagonal(rank, idxType, sparseLayoutType);
  var locDoms: [dist.targetLocDom] LocDiagonalDom(rank, idxType, stridable);
  var whole: domain(rank=rank, idxType=idxType, stridable=stridable);
}

//
// Local Diagonal Domain Class
//
// rank: generic domain rank
// idxType: generic domain index type
// stridable: generic domain stridable parameter
// myBlock: a non-distributed domain that defines the local indices
//
class LocDiagonalDom {
  param rank: int;
  type idxType;
  param stridable: bool;
  var myBlock: domain(rank, idxType, stridable);
  var myStorageBlock: domain(1, idxType, stridable);
}

//
// Diagonal Array Class
//
// eltType: generic array element type
// rank: generic array rank
// idxType: generic array index type
// stridable: generic array stridable parameter
// dom: reference to domain class
// locArr: a non-distributed array of local array classes
// myLocArr: optimized reference to here's local array class (or nil)
//
class DiagonalArr: BaseArr {
  type eltType;
  param rank: int;
  type idxType;
  param stridable: bool;
  type sparseLayoutType;
  var dom: DiagonalDom(rank, idxType, stridable, sparseLayoutType);
  var locArr: [dom.dist.targetLocDom] LocDiagonalArr(eltType, rank, idxType, stridable);
  var myLocArr: LocDiagonalArr(eltType, rank, idxType, stridable);
}

//
// Local Diagonal Array Class
//
// eltType: generic array element type
// rank: generic array rank
// idxType: generic array index type
// stridable: generic array stridable parameter
// locDom: reference to local domain class
// myElems: a non-distributed array of local elements
//
class LocDiagonalArr {
  type eltType;
  param rank: int;
  type idxType;
  param stridable: bool;
  const locDom: LocDiagonalDom(rank, idxType, stridable);
  // TODO diagonal - adjust
  var myElems: [locDom.myStorageBlock] eltType;
}

//
// Diagonal constructor for clients of the Diagonal distribution
//
proc Diagonal.Diagonal(boundingBox: domain,
                targetLocales: [] locale = Locales,
                param rank = boundingBox.rank,
                type idxType = boundingBox.idxType,
                type sparseLayoutType = DefaultDist) {
  if rank != boundingBox.rank then
    compilerError("specified Diagonal rank != rank of specified bounding box");
  if idxType != boundingBox.idxType then
    compilerError("specified Diagonal index type != index type of specified bounding box");
/* TODO diagonal - let's not "use LayoutCSR;" just for this check:
  if rank != 2 && sparseLayoutType == CSR then 
    compilerError("CSR layout is only supported for 2 dimensional domains");
*/
  // TODO diagonal - need this?
  if rank != 2 then 
    compilerError("Diagonal is only supported for 2-dimensional domains");

  if boundingBox.size == 0 then
    halt("Diagonal() requires a non-empty boundingBox");

  this.boundingBox = boundingBox : domain(rank, idxType, stridable = false);

  setupTargetLocalesArray(targetLocDom, this.targetLocales, targetLocales);

  const boundingBoxDims = this.boundingBox.dims();
  const targetLocDomDims = targetLocDom.dims();
  coforall locid in targetLocDom do
    on this.targetLocales(locid) do
      locDist(locid) =  new LocDiagonal(rank, idxType, locid, boundingBoxDims,
                                     targetLocDomDims);

  if debugDiagonalDist {
    writeln("Creating new Diagonal distribution:");
    dsiDisplayRepresentation();
  }
}

proc Diagonal.dsiAssign(other: this.type) {
  coforall locid in targetLocDom do
    on targetLocales(locid) do
      delete locDist(locid);
  boundingBox = other.boundingBox;
  targetLocDom = other.targetLocDom;
  targetLocales = other.targetLocales;
  const boundingBoxDims = boundingBox.dims();
  const targetLocDomDims = targetLocDom.dims();

  coforall locid in targetLocDom do
    on targetLocales(locid) do
      locDist(locid) = new LocDiagonal(rank, idxType, locid, boundingBoxDims,
                                    targetLocDomDims);
}

//
// Diagonal distributions are equivalent if they share the same bounding
// box and target locale set.
//
proc Diagonal.dsiEqualDMaps(that: Diagonal(?)) {
  return (this.boundingBox == that.boundingBox &&
          this.targetLocales.equals(that.targetLocales));
}

//
// Diagonal distributions are not equivalent to other domain maps.
//
proc Diagonal.dsiEqualDMaps(that) param {
  return false;
}

proc Diagonal.dsiClone() {
  return new Diagonal(boundingBox, targetLocales,
                   rank,
                   idxType,
                   sparseLayoutType);
}

proc Diagonal.dsiDestroyDist() {
  coforall ld in locDist do {
    on ld do
      delete ld;
  }
}

proc Diagonal.dsiDisplayRepresentation() {
  writeln("boundingBox = ", boundingBox);
  writeln("targetLocDom = ", targetLocDom);
  writeln("targetLocales = ", for tl in targetLocales do tl.id);
  for tli in targetLocDom do
    writeln("locDist[", tli, "].myChunk = ", locDist[tli].myChunk);
}

proc Diagonal.dsiNewRectangularDom(param rank: int, type idxType,
                                param stridable: bool, inds) {
  if idxType != this.idxType then
    compilerError("Diagonal domain index type does not match distribution's");
  if rank != this.rank then
    compilerError("Diagonal domain rank does not match distribution's");

  var dom = new DiagonalDom(rank=rank, idxType=idxType, dist=this,
      stridable=stridable, sparseLayoutType=sparseLayoutType);
  dom.dsiSetIndices(inds);
  if debugDiagonalDist {
    writeln("Creating new Diagonal domain:");
    dom.dsiDisplayRepresentation();
  }
  return dom;
}

proc Diagonal.dsiNewSparseDom(param rank: int, type idxType, dom: domain) {
  return new SparseDiagonalDom(rank=rank, idxType=idxType,
      sparseLayoutType=sparseLayoutType, dist=this, whole=dom._value.whole, 
      parentDom=dom);
}

//
// output distribution
//
proc Diagonal.writeThis(x) {
  x.writeln("Diagonal");
  x.writeln("-------");
  x.writeln("distributes: ", boundingBox);
  x.writeln("across locales: ", targetLocales);
  x.writeln("indexed via: ", targetLocDom);
  x.writeln("resulting in: ");
  for locid in targetLocDom do
    x.writeln("  [", locid, "] locale ", locDist(locid).locale.id, " owns chunk: ", locDist(locid).myChunk);
}

proc Diagonal.dsiIndexToLocale(ind: idxType) where rank == 1 {
  return targetLocales(targetLocsIdx(ind));
}

proc Diagonal.dsiIndexToLocale(ind: rank*idxType) {
  return targetLocales(targetLocsIdx(ind));
}

//
// compute what chunk of inds is owned by a given locale -- assumes
// it's being called on the locale in question
//
// TODO diagonal - adjust
//
proc Diagonal.getChunk(inds, locid) {
  // use domain slicing to get the intersection between what the
  // locale owns and the domain's index set
  //
  // TODO: Should this be able to be written as myChunk[inds] ???
  //
  // TODO: Does using David's detupling trick work here?
  //
  const chunk = locDist(locid).myChunk((...inds.getIndices()));
  return chunk;
}

//
// get the index into the targetLocales array for a given distributed index
//
proc Diagonal.targetLocsIdx(ind: idxType) where rank == 1 {
  return targetLocsIdx((ind,));
}

// TODO diagonal - adjust
proc Diagonal.targetLocsIdx(ind: rank*idxType) {
  var result: rank*int;
  for param i in 1..rank do
    result(i) = max(0, min((targetLocDom.dim(i).length-1):int,
                           (((ind(i) - boundingBox.dim(i).low) *
                             targetLocDom.dim(i).length:idxType) /
                            boundingBox.dim(i).length):int));
  return if rank == 1 then result(1) else result;
}

// TODO diagonal - adjust
// constructor
proc LocDiagonal.LocDiagonal(param rank: int,
                      type idxType, 
                      locid, // the locale index from the target domain
                      boundingBox: rank*range(idxType),
                      targetLocBox: rank*range) {
  if rank == 1 {
    const lo = boundingBox(1).low;
    const hi = boundingBox(1).high;
    const numelems = hi - lo + 1;
    const numlocs = targetLocBox(1).length;
    const (blo, bhi) = _computeBlock(numelems, numlocs, locid,
                                     max(idxType), min(idxType), lo);
    myChunk = {blo..bhi};
  } else {
    var inds: rank*range(idxType);
    for param i in 1..rank {
      const lo = boundingBox(i).low;
      const hi = boundingBox(i).high;
      const numelems = hi - lo + 1;
      const numlocs = targetLocBox(i).length;
      const (blo, bhi) = _computeBlock(numelems, numlocs, locid(i),
                                       max(idxType), min(idxType), lo);
      inds(i) = blo..bhi;
    }
    myChunk = {(...inds)};
  }
}


proc DiagonalDom.dsiMyDist() return dist;

proc DiagonalDom.dsiDisplayRepresentation() {
  writeln("whole = ", whole);
  for tli in dist.targetLocDom do
    writeln("locDoms[", tli, "].myBlock = ", locDoms[tli].myBlock);
}

proc DiagonalDom.dsiDims() return whole.dims();

proc DiagonalDom.dsiDim(d: int) return whole.dim(d);

// stopgap to avoid accessing locDoms field (and returning an array)
proc DiagonalDom.getLocDom(localeIdx) return locDoms(localeIdx);


// TODO diagonal - needed?
//
// Given a tuple of scalars of type t or range(t) match the shape but
// using types rangeType and scalarType e.g. the call:
// _matchArgsShape(range(int(32)), int(32), (1:int(64), 1:int(64)..5, 1:int(64)..5))
// returns the type: (int(32), range(int(32)), range(int(32)))
//
proc _matchArgsShape(type rangeType, type scalarType, args) type {
  proc helper(param i: int) type {
    if i == args.size {
      if isCollapsedDimension(args(i)) then
        return (scalarType,);
      else
        return (rangeType,);
    } else {
      if isCollapsedDimension(args(i)) then
        return (scalarType, (... helper(i+1)));
      else
        return (rangeType, (... helper(i+1)));
    }
  }
  return helper(1);
}


// TODO diagonal - adjust
iter DiagonalDom.these() {
  for i in whole do
    yield i;
}

// TODO diagonal - adjust
iter DiagonalDom.these(param tag: iterKind) where tag == iterKind.leader {
  const wholeLow = whole.low;

  const hereId = here.id;
  coforall locDom in locDoms do on locDom {
    // Use the internal function for untranslate to avoid having to do
    // extra work to negate the offset
    type strType = chpl__signedType(idxType);
    const tmpBlock = locDom.myBlock.chpl__unTranslate(wholeLow);
    var locOffset: rank*idxType;
    for param i in 1..tmpBlock.rank {
      const stride = tmpBlock.dim(i).stride;
      if stride < 0 && strType != idxType then
        halt("negative stride not supported with unsigned idxType");
        // (since locOffset is unsigned in that case)
      locOffset(i) = tmpBlock.dim(i).first / stride:idxType;
    }
    // Forward to defaultRectangular
    for followThis in tmpBlock._value.these(tag=iterKind.leader,
                                            offset=locOffset) do
      yield followThis;
  }
}

//
// TODO: Abstract the addition of low into a function?
// Note relationship between this operation and the
// order/position functions -- any chance for creating similar
// support? (esp. given how frequent this seems likely to be?)
//
// TODO: Is there some clever way to invoke the leader/follower
// iterator on the local blocks in here such that the per-core
// parallelism is expressed at that level?  Seems like a nice
// natural composition and might help with my fears about how
// stencil communication will be done on a per-locale basis.
//
iter DiagonalDom.these(param tag: iterKind, followThis) where tag == iterKind.follower {
  proc anyStridable(rangeTuple, param i: int = 1) param
      return if i == rangeTuple.size then rangeTuple(i).stridable
             else rangeTuple(i).stridable || anyStridable(rangeTuple, i+1);

  if chpl__testParFlag then
    chpl__testParWriteln("Diagonal domain follower invoked on ", followThis);

  var t: rank*range(idxType, stridable=stridable||anyStridable(followThis));
  type strType = chpl__signedType(idxType);
  for param i in 1..rank {
    var stride = whole.dim(i).stride: strType;
    // not checking here whether the new low and high fit into idxType
    var low = (stride * followThis(i).low:strType):idxType;
    var high = (stride * followThis(i).high:strType):idxType;
    t(i) = ((low..high by stride:strType) + whole.dim(i).low by followThis(i).stride:strType).safeCast(t(i).type);
  }
  for i in {(...t)} {
    yield i;
  }
}

//
// output domain
//
proc DiagonalDom.dsiSerialWrite(x) {
  x.write(whole);
}

//
// how to allocate a new array over this domain
//
proc DiagonalDom.dsiBuildArray(type eltType) {
  var arr = new DiagonalArr(eltType=eltType, rank=rank, idxType=idxType,
      stridable=stridable, sparseLayoutType=sparseLayoutType, dom=this);
  arr.setup();
  return arr;
}

// TODO diagonal - adjust
proc DiagonalDom.dsiNumIndices return whole.numIndices;
proc DiagonalDom.dsiLow return whole.low;
proc DiagonalDom.dsiHigh return whole.high;
proc DiagonalDom.dsiStride return whole.stride;
proc DiagonalDom.dsiAlignedLow return whole.alignedLow;
proc DiagonalDom.dsiAlignedHigh return whole.alignedHigh;
proc DiagonalDom.dsiAlignment return whole.alignment;

//
// INTERFACE NOTES: Could we make dsiSetIndices() for a rectangular
// domain take a domain rather than something else?
//
proc DiagonalDom.dsiSetIndices(x: domain) {
  if x.rank != rank then
    compilerError("rank mismatch in domain assignment");
  if x._value.idxType != idxType then
    compilerError("index type mismatch in domain assignment");
  whole = x;
  setup();
  if debugDiagonalDist {
    writeln("Setting indices of Diagonal domain:");
    dsiDisplayRepresentation();
  }
}

proc DiagonalDom.dsiSetIndices(x) {
  if x.size != rank then
    compilerError("rank mismatch in domain assignment");
  if x(1).idxType != idxType then
    compilerError("index type mismatch in domain assignment");
  //
  // TODO: This seems weird:
  //
  whole.setIndices(x);
  setup();
  if debugDiagonalDist {
    writeln("Setting indices of Diagonal domain:");
    dsiDisplayRepresentation();
  }
}

proc DiagonalDom.dsiGetIndices() {
  return whole.getIndices();
}

// dsiLocalSlice
proc DiagonalDom.dsiLocalSlice(param stridable: bool, ranges) {
  return whole((...ranges));
}

proc DiagonalDom.setup() {
  if locDoms(dist.targetLocDom.low) == nil {
    coforall localeIdx in dist.targetLocDom do {
      on dist.targetLocales(localeIdx) do
        locDoms(localeIdx) = new LocDiagonalDom(rank, idxType, stridable,
                                             dist.getChunk(whole, localeIdx));
    }
  } else {
    coforall localeIdx in dist.targetLocDom do {
      on dist.targetLocales(localeIdx) {
        locDoms(localeIdx).myBlock = dist.getChunk(whole, localeIdx);
        locDoms(localeIdx).myStorageBlock = {locDoms(localeIdx).myBlock.dim(1)};
      }
    }
  }
}

proc DiagonalDom.dsiDestroyDom() {
  coforall localeIdx in dist.targetLocDom do {
    on locDoms(localeIdx) do
      delete locDoms(localeIdx);
  }
}

proc DiagonalDom.dsiMember(i) {
  return whole.member(i);
}

proc DiagonalDom.dsiIndexOrder(i) {
  return whole.indexOrder(i);
}

//
// Added as a performance stopgap to avoid returning a domain
//
proc LocDiagonalDom.member(i) return myBlock.member(i);

proc DiagonalArr.dsiDisplayRepresentation() {
  for tli in dom.dist.targetLocDom {
    writeln("locArr[", tli, "].myElems = ", for e in locArr[tli].myElems do e);
  }
}

proc DiagonalArr.dsiGetBaseDom() return dom;

proc DiagonalArr.setup() {
  var thisid = this.locale.id;
  coforall localeIdx in dom.dist.targetLocDom {
    on dom.dist.targetLocales(localeIdx) {
      const locDom = dom.getLocDom(localeIdx);
      locArr(localeIdx) = new LocDiagonalArr(eltType, rank, idxType, stridable, locDom);
      if thisid == here.id then
        myLocArr = locArr(localeIdx);
    }
  }
}

proc DiagonalArr.dsiDestroyArr(isslice:bool) {
  coforall localeIdx in dom.dist.targetLocDom {
    on locArr(localeIdx) {
      delete locArr(localeIdx);
    }
  }
}

inline proc DiagonalArr.dsiLocalAccess(i: rank*idxType) ref {
  return myLocArr.this(i);
}

//
// the global accessor for the array
//
// TODO: Do we need a global bounds check here or in targetLocsIdx?
//
// By splitting the non-local case into its own function, we can inline the
// fast/local path and get better performance.
//
// BHARSH TODO: Should this argument have the 'const in' intent? If it is
// remote, the commented-out local block will fail.
//

// 2D -> 1D
inline proc DiagonalArr.dsiAccess(idx: rank*idxType) ref {
  local {
    // TODO update locDom.member
    if myLocArr != nil && myLocArr.locDom.member(idx) then
      return myLocArr.this(idx);
  }
  return nonLocalAccess(idx);
}

proc DiagonalArr.nonLocalAccess(i: rank*idxType) ref {
  return locArr(dom.dist.targetLocsIdx(i)).this(i);
}
//
//proc DiagonalArr.dsiAccess(i: idxType...rank) ref
//  return dsiAccess(i);

iter DiagonalArr.these() ref {
  for i in dom do
    yield dsiAccess(i);
}

//
// TODO: Rewrite this to reuse more of the global domain iterator
// logic?  (e.g., can we forward the forall to the global domain
// somehow?
//
iter DiagonalArr.these(param tag: iterKind) where tag == iterKind.leader {
  for followThis in dom.these(tag) do
    yield followThis;
}

// TODO diagonal - need fast follow?
proc DiagonalArr.dsiStaticFastFollowCheck(type leadType) param
  return leadType == this.type || leadType == this.dom.type;

proc DiagonalArr.dsiDynamicFastFollowCheck(lead: [])
  return lead.domain._value == this.dom;

proc DiagonalArr.dsiDynamicFastFollowCheck(lead: domain)
  return lead._value == this.dom;

// TODO diagonal - fast follows?
iter DiagonalArr.these(param tag: iterKind, followThis, param fast: bool = false) ref where tag == iterKind.follower {
  proc anyStridable(rangeTuple, param i: int = 1) param
      return if i == rangeTuple.size then rangeTuple(i).stridable
             else rangeTuple(i).stridable || anyStridable(rangeTuple, i+1);

  if chpl__testParFlag {
    if fast then
      chpl__testParWriteln("Diagonal array fast follower invoked on ", followThis);
    else
      chpl__testParWriteln("Diagonal array non-fast follower invoked on ", followThis);
  }

  if testFastFollowerOptimization then
    writeln((if fast then "fast" else "regular") + " follower invoked for Diagonal array");

  var myFollowThis: rank*range(idxType=idxType, stridable=stridable || anyStridable(followThis));
  var lowIdx: rank*idxType;

  for param i in 1..rank {
    var stride = dom.whole.dim(i).stride;
    // NOTE: Not bothering to check to see if these can fit into idxType
    var low = followThis(i).low * abs(stride):idxType;
    var high = followThis(i).high * abs(stride):idxType;
    myFollowThis(i) = ((low..high by stride) + dom.whole.dim(i).low by followThis(i).stride).safeCast(myFollowThis(i).type);
    lowIdx(i) = myFollowThis(i).low;
  }

  const myFollowThisDom = {(...myFollowThis)};
  if fast {
    //
    // TODO: The following is a buggy hack that will only work when we're
    // distributing across the entire Locales array.  I still think the
    // locArr/locDoms arrays should be associative over locale values.
    //
    var arrSection = locArr(dom.dist.targetLocsIdx(lowIdx));

    //
    // if arrSection is not local and we're using the fast follower,
    // it means that myFollowThisDom is empty; make arrSection local so
    // that we can use the local block below
    //
    if arrSection.locale.id != here.id then
      arrSection = myLocArr;

    //
    // Slicing arrSection.myElems will require reference counts to be updated.
    // If myElems is an array of arrays, the inner array's domain or dist may
    // live on a different locale and require communication for reference
    // counting. Simply put: don't slice inside a local block.
    //
    ref chunk = arrSection.myElems(myFollowThisDom.dim(1));
    local {
      for i in chunk do yield i;
    }
  } else {
    //
    // we don't necessarily own all the elements we're following
    //
    for i in myFollowThisDom {
      yield dsiAccess(i);
    }
  }
}

proc DiagonalArr.dsiSerialRead(f) {
  chpl_serialReadWriteRectangular(f, this);
}

//
// output array
//
proc DiagonalArr.dsiSerialWrite(f) {
  type strType = chpl__signedType(idxType);
  var binary = f.binary();
  if dom.dsiNumIndices == 0 then return;
  var i : rank*idxType;
  for dim in 1..rank do
    i(dim) = dom.dsiDim(dim).low;
  label next while true {
    f.write(dsiAccess(i));
    if i(rank) <= (dom.dsiDim(rank).high - dom.dsiDim(rank).stride:strType) {
      if ! binary then f.write(" ");
      i(rank) += dom.dsiDim(rank).stride:strType;
    } else {
      for dim in 1..rank-1 by -1 {
        if i(dim) <= (dom.dsiDim(dim).high - dom.dsiDim(dim).stride:strType) {
          i(dim) += dom.dsiDim(dim).stride:strType;
          for dim2 in dim+1..rank {
            f.writeln();
            i(dim2) = dom.dsiDim(dim2).low;
          }
          continue next;
        }
      }
      break;
    }
  }
}

pragma "no copy return"
proc DiagonalArr.dsiLocalSlice(ranges) {
  var low: rank*idxType;
  for param i in 1..rank {
    low(i) = ranges(i).low;
  }
  return locArr(dom.dist.targetLocsIdx(low)).myElems((...ranges));
}

// TODO diagonal remove _extendTuple
proc _extendTuple(type t, idx: _tuple, args) {
  var tup: args.size*t;
  var j: int = 1;

  for param i in 1..args.size {
    if isCollapsedDimension(args(i)) then
      tup(i) = args(i);
    else {
      tup(i) = idx(j);
      j += 1;
    }
  }
  return tup;
}

proc _extendTuple(type t, idx, args) {
  var tup: args.size*t;
  var idxTup = (idx,);
  var j: int = 1;

  for param i in 1..args.size {
    if isCollapsedDimension(args(i)) then
      tup(i) = args(i);
    else {
      tup(i) = idxTup(j);
      j += 1;
    }
  }
  return tup;
}

proc DiagonalArr.dsiReallocate(d: domain) {
  //
  // For the default rectangular array, this function changes the data
  // vector in the array class so that it is setup once the default
  // rectangular domain is changed.  For this distributed array class,
  // we don't need to do anything, because changing the domain will
  // change the domain in the local array class which will change the
  // data in the local array class.  This will only work if the domain
  // we are reallocating to has the same distribution, but domain
  // assignment is defined so that only the indices are transferred.
  // The distribution remains unchanged.
  //
}

proc DiagonalArr.dsiPostReallocate() {
  // Call this *after* the domain has been reallocated
}

//
// the accessor for the local array -- assumes the index is local
//
// TODO: Should this be inlined?
//
proc LocDiagonalArr.this(i: rank*idxType) ref {
  var idx = i(1);
  return myElems(idx);
}

//
// Privatization
//
proc Diagonal.Diagonal(other: Diagonal, privateData,
                param rank = other.rank,
                type idxType = other.idxType,
                type sparseLayoutType = other.sparseLayoutType) {
  boundingBox = {(...privateData(1))};
  targetLocDom = {(...privateData(2))};

  for i in targetLocDom {
    targetLocales(i) = other.targetLocales(i);
    locDist(i) = other.locDist(i);
  }
}

proc Diagonal.dsiSupportsPrivatization() param return true;

proc Diagonal.dsiGetPrivatizeData() {
  return (boundingBox.dims(), targetLocDom.dims());
}

proc Diagonal.dsiPrivatize(privatizeData) {
  return new Diagonal(this, privatizeData);
}

proc Diagonal.dsiGetReprivatizeData() return boundingBox.dims();

proc Diagonal.dsiReprivatize(other, reprivatizeData) {
  boundingBox = {(...reprivatizeData)};
  targetLocDom = other.targetLocDom;
  targetLocales = other.targetLocales;
  locDist = other.locDist;
}

proc DiagonalDom.dsiSupportsPrivatization() param return true;

proc DiagonalDom.dsiGetPrivatizeData() return (dist.pid, whole.dims());

proc DiagonalDom.dsiPrivatize(privatizeData) {
  var privdist = chpl_getPrivatizedCopy(dist.type, privatizeData(1));
  // in constructor we have to pass sparseLayoutType as it has no default value
  var c = new DiagonalDom(rank=rank, idxType=idxType, stridable=stridable,
      sparseLayoutType=privdist.sparseLayoutType, dist=privdist);
  for i in c.dist.targetLocDom do
    c.locDoms(i) = locDoms(i);
  c.whole = {(...privatizeData(2))};
  return c;
}

proc DiagonalDom.dsiGetReprivatizeData() return whole.dims();

proc DiagonalDom.dsiReprivatize(other, reprivatizeData) {
  for i in dist.targetLocDom do
    locDoms(i) = other.locDoms(i);
  whole = {(...reprivatizeData)};
}

proc DiagonalArr.dsiSupportsPrivatization() param return true;

proc DiagonalArr.dsiGetPrivatizeData() return dom.pid;

proc DiagonalArr.dsiPrivatize(privatizeData) {
  var privdom = chpl_getPrivatizedCopy(dom.type, privatizeData);
  var c = new DiagonalArr(eltType=eltType, rank=rank, idxType=idxType,
      stridable=stridable, sparseLayoutType=sparseLayoutType, dom=privdom);
  for localeIdx in c.dom.dist.targetLocDom {
    c.locArr(localeIdx) = locArr(localeIdx);
    if c.locArr(localeIdx).locale.id == here.id then
      c.myLocArr = c.locArr(localeIdx);
  }
  return c;
}

proc DiagonalArr.dsiSupportsBulkTransfer() param {
    return false;
}
proc DiagonalArr.dsiSupportsBulkTransferInterface() param {
    return false;
}

proc DiagonalArr.doiCanBulkTransferStride(viewDom) param {
    return false;
}

proc DiagonalArr.dsiTargetLocales() {
  return dom.dist.targetLocales;
}

proc DiagonalDom.dsiTargetLocales() {
  return dist.targetLocales;
}

proc Diagonal.dsiTargetLocales() {
  return targetLocales;
}

// Diagonal subdomains are continuous
// TODO diagonal - adjust

proc DiagonalArr.dsiHasSingleLocalSubdomain() param return true;
proc DiagonalDom.dsiHasSingleLocalSubdomain() param return true;

// returns the current locale's subdomain

// TODO diagonal - adjust
proc DiagonalArr.dsiLocalSubdomain() {
  return myLocArr.locDom.myBlock;
}
proc DiagonalDom.dsiLocalSubdomain() {
  // TODO -- could be replaced by a privatized myLocDom in DiagonalDom
  // as it is with DiagonalArr
  var myLocDom:LocDiagonalDom(rank, idxType, stridable) = nil;
  for (loc, locDom) in zip(dist.targetLocales, locDoms) {
    if loc == here then
      myLocDom = locDom;
  }
  return myLocDom.myBlock;
}
