//! Exercise generated field operations; these tests never access MMIO.
//!
//! Each write infers its register's value type from a matching-width integer.
//! Compile this example without executing hardware accesses:
//! ```no_run
//! use fixture_api::FIXTURE0;
//! unsafe {
//!     FIXTURE0.byte.write(0xff_u8.into());
//!     FIXTURE0.half.write(0xffff_u16.into());
//!     FIXTURE0.word.write(0xffff_ffff_u32.into());
//!     FIXTURE0.double.write(0xffff_ffff_ffff_ffff_u64.into());
//! }
//! ```
//!
//! Same-width registers still reject one another's values, even address aliases:
//! ```compile_fail
//! use fixture_api::{fixture, FIXTURE0};
//! let other = fixture::alias::Value::from_bits(0);
//! unsafe { FIXTURE0.word.write(other); }
//! ```
//!
//! Conversion does not provide an implicit bridge between register types:
//! ```compile_fail
//! use fixture_api::{fixture, FIXTURE0};
//! let other = fixture::alias::Value::from_bits(0);
//! unsafe { FIXTURE0.word.write(other.into()); }
//! ```
//!
//! Integer conversion cannot silently narrow a value:
//! ```compile_fail
//! use fixture_api::FIXTURE0;
//! unsafe { FIXTURE0.word.write(u64::MAX.into()); }
//! ```
#[cfg(test)]
use fixture_api::*;

#[test]
fn integer_conversions_preserve_all_bits() {
    let byte: fixture::byte::Value = u8::MAX.into();
    let half: fixture::half::Value = u16::MAX.into();
    let word: fixture::word::Value = 0xdead_beef_u32.into();
    let double: fixture::double::Value = u64::MAX.into();
    assert_eq!(byte.bits(), u8::MAX);
    assert_eq!(half.bits(), u16::MAX);
    assert_eq!(word.bits(), 0xdead_beef);
    assert_eq!(double.bits(), u64::MAX);
}

#[test]
fn field_updates_preserve_other_bits_and_truncate() {
    let mut value = fixture::word::Value::from_bits(0xdead_beef);
    value.set_mode(0xff);
    assert_eq!(value.mode(), 7);
    assert_eq!(value.bits(), (0xdead_beef & !0x70) | 0x70);
    value.set_top(false);
    assert!(!value.top());
    assert_eq!(
        value.bits() & 0x7fff_ffff,
        ((0xdead_beef & !0x70) | 0x70) & 0x7fff_ffff
    );
    value.set_top(true);
    assert!(value.top());
}

#[test]
fn narrow_and_full_width_fields_work() {
    let mut byte = fixture::byte::Value::from_bits(0x78);
    byte.set_low(0xff);
    byte.set_high(true);
    assert_eq!(byte.bits(), 0xff);
    assert_eq!(byte.low(), 7);
    let mut half = fixture::half::Value::from_bits(0);
    half.set_all(u16::MAX);
    assert_eq!(half.all(), u16::MAX);
    half.set_all(0);
    assert_eq!(half.bits(), 0);
    let mut word = fixture::alias::Value::from_bits(0);
    word.set_all(u32::MAX);
    assert_eq!(word.all(), u32::MAX);
    word.set_all(0);
    assert_eq!(word.bits(), 0);
    let mut double = fixture::double::Value::from_bits(0);
    double.set_all(u64::MAX);
    assert_eq!(double.all(), u64::MAX);
    double.set_all(0);
    assert_eq!(double.bits(), 0);
}

#[test]
fn addresses_and_aliases_are_exact() {
    assert_eq!(FIXTURE0.byte.address(), 0x4000_0000);
    assert_eq!(FIXTURE0.half.address(), 0x4000_0002);
    assert_eq!(FIXTURE0.word.address(), 0x4000_0004);
    assert_eq!(FIXTURE0.alias.address(), FIXTURE0.word.address());
    assert_eq!(FIXTURE0.double.address(), 0x4000_0008);
    assert_eq!(core::mem::size_of::<fixture::byte::Value>(), 1);
    assert_eq!(core::mem::size_of::<fixture::half::Value>(), 2);
    assert_eq!(core::mem::size_of::<fixture::word::Value>(), 4);
    assert_eq!(core::mem::size_of::<fixture::double::Value>(), 8);
}
