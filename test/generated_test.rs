//! Exercise generated field operations; these tests never access MMIO.
include!(env!("REGISTER_FIXTURE"));

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
