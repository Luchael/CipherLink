import com.gametodo.nativeapp.TodoistOAuthPolicy as OAuth

fun main() {
    check(OAuth.REGISTER == "https://todoist.com/oauth/register")
    check(OAuth.AUTHORIZE == "https://todoist.com/oauth/authorize")
    check(OAuth.TOKEN == "https://todoist.com/oauth/access_token")
    check(OAuth.expiry(null, 1000) == 0L)
    check(OAuth.expiry(3600, 1000) == 3601000L)
    check(!OAuth.needsRefresh(0, 999999999))
    check(OAuth.needsRefresh(150000, 100000))
    check(OAuth.validCallback("/callback", "nonce", "nonce", "code"))
    check(!OAuth.validCallback("/favicon.ico", "nonce", "nonce", "code"))
    check(!OAuth.validCallback("/callback", "wrong", "nonce", "code"))
    check(!OAuth.validCallback("/callback", "nonce", "nonce", ""))
    println("Official OAuth routes, expiry and callback validation passed")
}
