import time
from django.test.runner import DiscoverRunner
from unittest import TextTestResult


class TimedTestResult(TextTestResult):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_timings = []
        self._start_time = None

    def startTest(self, test):
        self._start_time = time.perf_counter()
        super().startTest(test)

    def stopTest(self, test):
        elapsed = (time.perf_counter() - self._start_time) * 1000
        self.test_timings.append((str(test), elapsed))
        super().stopTest(test)

    def printTimingSummary(self):
        self.stream.writeln('\n' + '=' * 70)
        self.stream.writeln('TIMING SUMMARY')
        self.stream.writeln('=' * 70)

        total = sum(t for _, t in self.test_timings)
        passed = len(self.test_timings) - len(self.failures) - len(self.errors)
        total_tests = len(self.test_timings)
        pass_rate = (passed / total_tests * 100) if total_tests > 0 else 0
        fail_rate = 100 - pass_rate

        for name, elapsed in sorted(self.test_timings, key=lambda x: x[1], reverse=True):
            # Determine if this test passed or failed
            failed_names = [str(t) for t, _ in self.failures + self.errors]
            status = 'FAIL' if name in failed_names else 'PASS'
            marker = '✓' if status == 'PASS' else '✗'
            self.stream.writeln(f'  {marker} [{status}] {name:<55} {elapsed:>8.2f} ms')

        self.stream.writeln('-' * 70)
        self.stream.writeln(f'  Total tests   : {total_tests}')
        self.stream.writeln(f'  Passed        : {passed}  ({pass_rate:.1f}%)')
        self.stream.writeln(f'  Failed        : {len(self.failures) + len(self.errors)}  ({fail_rate:.1f}%)')
        self.stream.writeln(f'  Total time    : {total:.2f} ms')
        self.stream.writeln(f'  Avg per test  : {total / total_tests:.2f} ms' if total_tests > 0 else '')
        self.stream.writeln(f'  Slowest test  : {self.test_timings[0][0] if self.test_timings else "N/A"}')
        self.stream.writeln('=' * 70 + '\n')


class TimedTestRunner(DiscoverRunner):

    def get_resultclass(self):
        return TimedTestResult

    def run_suite(self, suite, **kwargs):
        result = super().run_suite(suite, **kwargs)
        if hasattr(result, 'printTimingSummary'):
            result.printTimingSummary()
        return result