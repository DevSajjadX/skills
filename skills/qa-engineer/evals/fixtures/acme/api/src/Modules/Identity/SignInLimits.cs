// Fixture values for QA evals. Fake.
public static class SignInLimits
{
    public static readonly TimeSpan ResendWait = TimeSpan.FromSeconds(90); // line 5
    public const int VerifyAttempts = 4;                                   // per 15 minutes
}
