# The goal for tonight

Working title: Tap to deduct. Sami set it on 17.09.2026, before the 19:00 brief. If the brief points
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
