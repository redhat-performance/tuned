Contributing to Tuned
=====================

Submitting patches
------------------

All patches should be based on the most recent revision of Tuned, which is
available on [GitHub](https://github.com/redhat-performance/tuned).

Patches should be created using `git` and the commit message should generally
consist of three parts:
1. The first line, which briefly describes the change that you are making.
2. A detailed description of the change. This should include information
   about the purpose of the change, i.e. why you are making the change in
   the first place. For example, if your patch addresses a bug, give
   a description of the bug and a way to reproduce it, if possible. If your
   patch adds a new feature, describe how it can be used and what it can be
   used for.

   Think about the impact that your change can have on the users. If your
   patch changes the behavior in a user-visible way, you should mention it
   and justify why the change should be made anyway.

   You should also describe any non-trivial design decisions that were made
   in making of the patch. Write down any gotchas that could be useful for
   future readers of the code, any hints that could be useful to determine
   why the change was made in a particular way.

   You can also provide links, for example links to any documentation that
   could be useful for reviewers of the patch, or links to discussions about
   a bug that your patch addresses. If your patch resolves a bug in the Red Hat
   Bugzilla, you can link to it using the following tag:

   `Resolves: rhbz#1592743`

   If your patch addresses an issue in the GitHub repository, you can use
   the following notation:

   `Fixes #95`
3. Your sign-off. Every commit needs to have a `Signed-off-by` tag at the end
   of the commit message, indicating that the contributor of the patch agrees
   with the [Developer Certificate of Origin](/DCO). The tag should have the
   following format and it must include the real name and email address of
   the contributor:

   `Signed-off-by: John Doe <jdoe@somewhere.com>`

   If you use `git commit -s`, `git` will add the tag for you.

Every patch should represent a single logical change. On the one hand, each
patch should be complete enough so that after applying it, the Tuned repository
remains in a consistent state and Tuned remains, to the best of the
contributor's knowledge, completely functional (a corollary of this is that
when making fixes to your pull request on GitHub, you should include the fixes
in the commits where they logically belong rather than appending new commits).

On the other hand, a patch should not make multiple changes which could be
separated into individual ones.

Patches can either be submitted in the form of pull requests to the GitHub
repository, sent to the power-management (at) lists.fedoraproject.org mailing
list, or sent directly to the maintainers of the Tuned project.

These guidelines were inspired by the [contribution guidelines of the Linux
Kernel](https://www.kernel.org/doc/html/latest/process/submitting-patches.html).
You can find more rationale for Tuned's guidelines in that document.
