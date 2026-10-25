import { equalWeights, fromBasisPoints, toBasisPoints, totalBasisPoints } from '@/lib/weights'

test('weights become exact basis points', () => {
  expect(toBasisPoints('33.33')).toBe(3333)
  expect(toBasisPoints('60')).toBe(6000)
  expect(toBasisPoints('0.5')).toBe(50)
  expect(toBasisPoints('100')).toBe(10000)
  for (const bad of ['', 'abc', '100.01', '1.234', '-5', '1e2']) {
    expect(toBasisPoints(bad)).toBeNull()
  }
})

test('totals are exact where floats are not', () => {
  // 0.1 + 0.2 is 0.30000000000000004 in floating point; here it's exactly 0.3
  expect(totalBasisPoints(['0.1', '0.2', '99.7'])).toBe(10000)
  expect(totalBasisPoints(['60', 'x'])).toBeNull()
  expect(fromBasisPoints(3333)).toBe('33.33')
  expect(fromBasisPoints(6000)).toBe('60')
  expect(fromBasisPoints(5)).toBe('0.05')
  expect(fromBasisPoints(9990)).toBe('99.9')
})

test('equal weights always add up to 100', () => {
  expect(equalWeights(3)).toEqual(['33.34', '33.33', '33.33'])
  expect(equalWeights(4)).toEqual(['25', '25', '25', '25'])
  expect(equalWeights(7).reduce((sum, w) => sum + toBasisPoints(w)!, 0)).toBe(10000)
  expect(equalWeights(0)).toEqual([])
})
