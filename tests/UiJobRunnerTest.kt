import com.gametodo.nativeapp.UiJobRunner
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

fun main() {
    val events=AtomicInteger();val errors=AtomicInteger()
    val first=CountDownLatch(1);val release=CountDownLatch(1);val details=CountDownLatch(1)
    val completed=CountDownLatch(2)
    val runner=UiJobRunner {events.incrementAndGet()}
    try {
        check(runner.submit("sync","sync",{completed.countDown()},{errors.incrementAndGet();completed.countDown()}) {
            first.countDown();release.await();error("simulated timeout")
        })
        check(first.await(2,TimeUnit.SECONDS))
        // The actual report: first job hangs/fails; the first progress click still succeeds.
        check(runner.submit("details","loading",{completed.countDown()},{error("details failed")}) {
            runner.update("details","스타레일 조회 중")
            check(runner.snapshot()["details"]=="스타레일 조회 중")
            details.countDown();"loaded"
        })
        check(details.await(2,TimeUnit.SECONDS)) {"Progress request was blocked by unrelated job"}
        check(runner.snapshot()["sync"]=="sync")
        check(!runner.submit("sync","duplicate",{}, {}) {error("duplicate request")})
        release.countDown();check(completed.await(2,TimeUnit.SECONDS))
        check(errors.get()==1 && runner.snapshot().isEmpty())
        val retry=CountDownLatch(1)
        check(runner.submit("sync","retry",{retry.countDown()},{error("retry failed")}) {"ok"})
        check(retry.await(2,TimeUnit.SECONDS))
    } finally {release.countDown();runner.close()}
    check(!runner.submit("closed","",{}, {}) {"must not execute"})
    check(events.get()>=4)
    println("UiJobRunner: hung/failing sync, independent details, duplicate tap, retry and cleanup passed")
}
