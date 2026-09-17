# The goal for tonight

Working title: Tap to deduct. Sami set it on 17.09.2026 before the brief, and a Taxfix employee
validated it on the night: pay in the shop, get the eligibility answer back immediately, and when it is
eligible the push asks for the photo right then. Same person confirmed the bank route, every bank has to
expose the account API and Taxfix can sit on it. If the brief points
elsewhere, this is the fallback we already know how to build.

## In one sentence

You pay with the business card, and before the receipt printer stops, your phone asks one question:
this looks deductible, add it? One tap and it is in the tax file.

## The flow

1. Apple Pay transaction on the business card fires a Shortcuts automation on the phone.
2. The automation posts amount, merchant, card and time to our endpoint.
3. The router answers in under a second: deductible or not, the category, the rule it used, the
   estimated tax effect in euros.
4. The phone shows one question with three answers: yes, no, or photograph the receipt.
5. Yes writes the entry into the tax file. No writes a rule so that merchant never asks again.

Friday evening, one push: want to see what this week was worth? Numbers, not a dashboard.

## What the card actually gives us

The Wallet trigger carries amount, merchant string, card and timestamp. That is thinner than it sounds
and further than it sounds.

- It is enough to decide most cases. AWS, Adobe, DB Vertrieb, a hardware shop: the merchant alone
  settles it. Repetition settles the rest, because a merchant you answered once never asks again.
- It is not enough for the ambiguous ones. A supermarket can be lunch or a client dinner, a marketplace
  can be anything, a card terminal string like "SUMUP *K42" is nothing at all. The answer there is not a
  receipt, it is one question with two buttons.
- Taxfix has the unfair advantage here: millions of users have already classified the same merchants.
  Nobody else can answer "SUMUP *K42" from the crowd. That is the line that makes this their product
  and not a side project.

## Does it need a receipt

Not to file. Since 2017 the return carries the numbers, not the paper: you keep the receipts and hand
them over only if the office asks. So the app works end to end without a single photo. Check the detail
with a Taxfix tax person before the stage, they are standing in the room.

Where paper is unavoidable:

- Input tax for a business needs an invoice under section 14 UStG. No invoice, no input tax.
- Client entertainment has its own rules and the card never covers them.
- If the office does ask and the receipt is missing, the deduction can fall away.

So the receipt is insurance, not a gate. The entry goes in on the tap. The app tracks which entries
stand on a card charge alone and shows that as a risk, quietly, instead of nagging for a photo. The
mail matching on amount, date and merchant fills most of them in later without the user doing anything.

## Can we just generate the receipt ourselves

Half yes, and the half matters.

What we must never do is print a PDF that looks like the merchant issued it. A receipt comes from the
seller. Building one that imitates their invoice is forgery, and saying it on this stage would end the
pitch in the room.

What we may do is the Eigenbeleg, the self written voucher every bookkeeper already uses when a paper
slip is lost: payee, date, amount, what it was for, why there is no original, signed. It is accepted for
small and unavoidable cases, parking, vending, a lost slip. It is never enough for input tax, which
always needs the seller's invoice under section 14 UStG. So we generate it, we label it as what it is,
and we never let it cover VAT.

The better move is to fetch the real one instead of writing one. German B2B e-invoicing has been
mandatory to receive since January 2025, and Malek already built the einvoice reader in spine. Card
charge triggers the case, the e-invoice or the invoice mail closes it, the Eigenbeleg fills the gap that
is left. That chain is the demo nobody else in the room will have.

## Filling the reason from the register

Sami's idea, and it is the one that makes the single tap possible: do not ask the user what the expense
was for, look the merchant up and propose it.

- The German commercial register has been free to query since 2022 and carries each company's stated
  purpose in words. Resolve the merchant, read the purpose, propose the category. Office supplies from a
  company whose register entry says trade in office goods writes its own line.
- Resolving the merchant is the hard half. Card descriptors are mangled, "SUMUP *K42" names nobody. Three
  fallbacks in order: our own history for this user, what other users already answered for that same
  descriptor, then the register or a places lookup. The merchant category code would settle it outright,
  and the Wallet trigger does not carry it. Bank data over PSD2 usually does. One more reason the
  production path is the bank, not the phone.
- What the register cannot know is why it was business. Deductibility is about the reason for the spend,
  not the seller's trade. So the register fills the draft and the user confirms it with the same tap that
  files the entry. Proposed by us, confirmed by them, logged as both.
- Entertainment stays manual. The law wants the occasion and the people at the table, and no lookup
  invents those.

Auto filling a reason nobody confirmed would be writing the user's statement for them. Proposing one they
accept in a tap is the product.

## Line items, and what the agent may learn

A supermarket charge is one number for a basket that was half private. The receipt line items are the
only thing that splits it, and the shops already have them: REWE and Lidl and dm all issue a digital
receipt in their own app, with articles and VAT rates on it.

The legal way to get them is the user's own copy, never the shop's app. Three doors, in order: the
receipt mail forwarded into the same inbox we already match invoices in, the export the user is entitled
to under GDPR article 20, and the photo. Scraping a shop app or holding a user's login for it is off the
table, it breaks their terms and it is the kind of thing that ends a partnership conversation. The door
that scales is a digital receipt network, and Taxfix is big enough to be the one that asks.

The learning agent is the right shape here, with one rule that must not bend: frequency is not a reason.

- Learn per merchant and context, not per merchant alone. Repeat visits to a supermarket are evidence of
  groceries, not of business. Turning "often at REWE" into an automatic yes is how a user ends up signing
  a return they never read.
- Auto file only what the user has answered the same way several times, only under a value limit, and
  only where the category is unambiguous. Software subscription yes, supermarket no.
- Everything auto filed appears in the Friday summary as a list that can be revoked with one tap. The
  user has to be able to see what was decided for them before it is filed.
- The audit trail stores who decided each entry: rule, model, or human. When the office asks two years
  later, that column is the difference between an answer and a problem.

## Decided on the night: always a photo

We dropped the automatic path. Sometimes filing by itself and sometimes asking is a coin flip the user
cannot predict, and an entry nobody looked at is an entry they signed blind. One rule instead: every
entry carries a photo of the receipt, no exceptions.

What it costs: some people will not take the picture, and those expenses are lost. We accept that.

What it buys, and this is the pitch:

- Every entry survives an audit, input tax included. Nothing in the file rests on a card charge alone.
- The moment is right. The push arrives while the paper is still in your hand, which is the only moment
  it ever exists. At home the receipt is gone. That is why the trigger has to be the payment itself.
- The flow is one line with no branches: pay, answer, photo, filed. It demos in thirty seconds.

The classifier does not disappear, it changes job. It decides whether to ask at all, so a private card at
a supermarket never interrupts anyone, and it reads the photo afterwards for amount, VAT, line items and
merchant, and files the entry. No photo, no entry, and the reminder expires with the day.

## Two things that must be right

- The saving is not the amount spent. It is the amount times the marginal rate, or the input tax for a
  business. Showing 24,90 EUR saved on a 24,90 EUR lunch is wrong and this jury knows it. We show the
  estimate with the rate visible, and we call it an estimate.
- The business card is the signal. If someone pays with it, the default flips to deductible and we ask
  only about the exceptions. That halves the questions on day one and the rules kill the rest by week two.

## On stage

Sami pays one euro from the stage with his own phone. The question arrives while he is still talking.
He taps yes. The entry appears in the file on screen. A saved run stands ready in case the wifi dies.

## What we do not build tonight

No native app, no bank connection, no filing. We say the production path in one line: Shortcuts is the
demo, PSD2 bank data is the product, and Taxfix already has the banking rails.

## Open before 19:00

- Does the brief allow a consumer facing flow, or is it internal tooling only
- Who writes the entry: our own file, or the spine tax structure Malek built
- Name
