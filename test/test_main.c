#include <stdio.h>

#include "test/test_header.h"

int main(void) {
  printf("SPI0: %p\n", SPI0);
  printf("SPI3: %p\n", SPI[3]);
}
