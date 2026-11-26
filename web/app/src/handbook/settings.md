# Settings and access

## Make the workspace yours

Open **Settings** in the workspace sidebar. Choose **System**, **Light** or **Dark** for Appearance. System follows your device. On a narrow screen, use **Browse workspace** to open the sidebar.

**Show Stead Handbook in Projects** controls the Handbook entry for your account in this browser. Turn it off to shorten your project list. Return to Settings and turn it on to restore the entry. A saved Handbook link still opens while the entry is hidden.

## What other people see

The name at the top of Stead belongs to the signed-in account. The Urbit ID shown with it identifies the ship that approved the session. For a galaxy, star or planet, Stead draws that ship’s sigil beside the name. Two ships can look alike at this size. Read the Urbit ID when you need to tell them apart.

Appearance applies to everyone using this browser profile. Each signed-in account chooses whether the Handbook appears in its own project list. Other projects show only when your Home has granted you access. If you expected a project, ask its maintainer to check which Urbit identity has membership.

## Sign in on the private pilot

Think of Home as the team's front door and your ship as the place where you answer, “Yes, that's me.” On the configured pilot computer, open both sites with `stead-pilot`.

1. On **Stead**, enter your Urbit ID and request sign-in. Home gives this browser a short-lived request and displays a comparison code.
2. On **Sign-in approval**, sign in to your own ship if prompted. Check that the Home address and the comparison code match what you see in Stead. Choose **Approve sign-in**. Your ship sends its approval directly to Home.
3. Return to the original Stead tab and choose **Open Stead** or **Check approval**. Home checks that the approval came from the ship on your current membership and that this is the browser that started the request. It uses that approval once and gives this browser a Stead session.

Your Urbit ID answers “Who is this?” Your project role answers “What can they do here?” A reader can open a shared page. A contributor can save an edit where the project allows it. Knowing someone’s ship name or comparison code alone gives you no project access.

The private tunnel gets this computer to the pilot. Sign-in establishes your Stead session. Git asks for its own repository credential when you clone or fetch. Keep your ship login code on your own ship’s login page. **Sign out** in Stead ends the Home session. The approval site has its own sign-out.
