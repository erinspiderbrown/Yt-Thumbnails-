# 002: High school coach allegedly gave athletes PEDs, two athletes suspended

Format: controversy / breaking news · long-form

## ✅ FINAL
- **Thumbnail:** `FINAL-thumbnail.png` (= v4, coach's face big, "WHAT DID HE GIVE THEM?", athletes as SUSPENDED cards)
- A/B test partner: `thumb-v5.png` ("COACH ACCUSED")

### Why v1–v3 were replaced
Three equal panels plus four text elements meant no focal point, faces too small at phone size,
and lime text on a yellow shirt. v4/v5 follow what the outliers do: one big face (~50% of frame),
2–4 huge words on the empty side, and the athletes as small supporting "evidence" cards
where the coach is looking.

Rebuild v4:
```bash
python ../../tools/make_thumbnail.py --photo photos/coach.jpg --zoom 1.3 --focus 0.40,0.36 \
  --layout left --text-width 0.52 --shade 0.85 --cards \
  --photo2 photos/athlete-1.jpg --focus2 0.5,0.33 --hide2 0.49,0.29,0.12,0.115 \
  --photo3 photos/athlete-2.jpg --focus3 0.5,0.35 --hide3 0.5,0.145,0.065,0.11 \
  --text "WHAT DID HE|*GIVE THEM?*" --tag ALLEGED --out thumb-v4.png
```
- **Title:** High School Coach Accused of Giving His Athletes PEDs, Now They're Suspended

## Earlier drafts (v1–v3, superseded)

## Thumbnails (all in house style, athletes' faces pixelated)
| File | Text | When to use |
|---|---|---|
| `thumb-v1.png` | COACH **ALLEGEDLY?** + "PED SCANDAL" tab | Safest wording. "Allegedly" is the hook |
| `thumb-v2.png` | WHAT DID COACH **GIVE THEM?** + "ALLEGED" tab | **Recommended.** Strongest curiosity gap; it's a question, and the "ALLEGED" tab covers you |
| `thumb-v3.png` | THE COACH **DID THIS?** + coach's face hidden too | Use if the coach hasn't been publicly named by a news outlet or governing body |

Rebuild any version (from this folder):
```bash
python ../../tools/make_thumbnail.py --layout trio --photo photos/coach.jpg --focus 0.5,0.4 \
  --photo2 photos/athlete-1.jpg --focus2 0.5,0.31 --hide2 0.49,0.29,0.12,0.115 \
  --photo3 photos/athlete-2.jpg --focus3 0.5,0.3 --hide3 0.5,0.145,0.065,0.11 \
  --label2 SUSPENDED --label3 SUSPENDED --shade 0.7 \
  --text "WHAT DID|COACH *GIVE THEM?*" --tag "ALLEGED" --out thumb-v2.png
```
To ALSO hide the coach's face, add `--hide 0.475,0.33,0.095,0.2`.

## Title options
Built from formulas that broke out in the niche (TRP "Situation", Final Leg "What Everyone Missed", Jumpman "Exposed a Huge Problem").
Not vidIQ-scored (out of credits). Score them when credits are back.

1. **High School Coach Accused of Giving His Athletes PEDs, Now They're Suspended** ← recommended (clear, searchable, "Accused" protects you)
2. This Coach Allegedly Gave His Athletes PEDs… And They're The Ones Paying For It
3. The High School PED Situation Is Getting Crazier
4. Two Sprinters Suspended Because of Their Coach? What We Know
5. What Everyone Is Missing About This High School Doping Scandal
6. This PED Scandal Exposed a Huge Problem in High School Track

Pair the thumbnail and title so they don't repeat: v2 ("What did coach give them?") + title 1.

## Before you publish: checklist
- [ ] Use "accused / allegedly / reportedly" in the title, the thumbnail and the first 30 seconds of the video. Cite your source (news article, governing-body notice) in the description.
- [ ] If either athlete is under 18, keep their faces hidden **and** consider cropping out the name bib. Right now the "HODGE" bib and BVI flag still identify athlete 2.
- [ ] Photo rights: the athlete-2 photo looks like a press/agency photo (Commonwealth Games). Commentary use is often fair use, but agency photos get copyright claims. Use your own screenshots from news coverage you're discussing, or credit the source.
- [ ] Don't say the coach *did* it unless a ruling says so. "Accused of" until proven.
