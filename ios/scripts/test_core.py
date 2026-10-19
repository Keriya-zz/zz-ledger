"""Run the same Foundation tests with Command Line Tools when XCTest is unavailable.

Full Xcode installations should use `swift test --package-path ios` instead.
This only tests Core, not UIKit, WebKit, iOS data protection or signing.
"""
from pathlib import Path
import os
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '.qa/ios-core-tests'
OUT.mkdir(parents=True, exist_ok=True)
tests = (ROOT / 'ios/Tests/LedgerStoreTests.swift').read_text()
tests = tests.replace('import XCTest', '').replace('@testable import ZZLedgerCore', '')
methods = re.findall(r'func (test\w+)\(\)', tests)
shim = r'''
class XCTestCase {
    func setUpWithError() throws {}
    func tearDownWithError() throws {}
}
func XCTAssertEqual<T: Equatable>(_ lhs: @autoclosure () throws -> T, _ rhs: @autoclosure () throws -> T) {
    do { let a = try lhs(); let b = try rhs(); if a != b { fatalError("Expected equal: \(a), \(b)") } }
    catch { fatalError("Unexpected error: \(error)") }
}
func XCTAssertNil<T>(_ value: @autoclosure () throws -> T?) {
    do { if try value() != nil { fatalError("Expected nil") } }
    catch { fatalError("Unexpected error: \(error)") }
}
func XCTAssertTrue(_ value: @autoclosure () throws -> Bool) {
    do { if try !value() { fatalError("Expected true") } }
    catch { fatalError("Unexpected error: \(error)") }
}
func XCTAssertThrowsError<T>(_ value: @autoclosure () throws -> T, file: StaticString = #file, line: UInt = #line) {
    do { _ = try value() } catch { return }
    fatalError("Expected an error", file: file, line: line)
}
'''
runner = '@main struct TestRunner { static func main() throws {\n'
for method in methods:
    runner += f'do {{ FileHandle.standardError.write(Data("RUN: {method}\\n".utf8)); let test = LedgerStoreTests(); try test.setUpWithError(); defer {{ try? test.tearDownWithError() }}; try test.{method}(); print("PASS: {method}") }}\n'
runner += '} }\n'
source = OUT / 'Runner.swift'
source.write_text(shim + tests + runner)
cache = ROOT / '.qa/swift-module-cache'
env = dict(os.environ, CLANG_MODULE_CACHE_PATH=str(cache))
subprocess.run(['swiftc', '-module-cache-path', str(cache),
                *map(str, sorted((ROOT / 'ios/ZZLedger/Core').glob('*.swift'))),
                str(source), '-o', str(OUT / 'core-tests')], check=True, env=env)
subprocess.run([str(OUT / 'core-tests')], check=True)
