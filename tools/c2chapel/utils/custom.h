#ifndef _C2CHAPEL_CUSTOM_H_
#define _C2CHAPEL_CUSTOM_H_

#define __attribute__(x)
#define __extension__(x)

/* Add your own definitions below! */
#define SDL_FORCE_INLINE // __inline__ not supported
#undef __cplusplus        // not C++
#undef __MMX__
#undef _MSC_VER
#undef _M_X64
#define _WIN64
//#define __BEGIN_DECLS
#undef HAVE_STRINGS_H // C does not have strings

#endif
