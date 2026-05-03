# JSM Cooperative Recovered WordPress Export Audit

Generated: 2026-05-02T21:31:18.633406Z

Source export: `jsmcooperative.WordPress.2026-05-02 (1).xml`

## Counts

- Published pages: 10
- Published posts: 9
- Feedback/contact entries: 9
- Published Mailchimp forms: 1
- WP Navigation records: 1

## Published pages recovered

| Page | Slug | Created | Modified | HTML length |
|---|---:|---:|---:|---:|
| Blogs | `/blogs/` | 2024-04-01 | 2025-11-22 | 19,237 |
| Chapter Readings: The Man in the Ballcap | `/chapter-readings/` | 2024-03-19 | 2024-04-06 | 9,388 |
| Contact Us | `/contactus/` | 2023-12-05 | 2025-11-23 | 4,086 |
| Donate | `/donate/` | 2024-03-27 | 2025-11-22 | 32,038 |
| Instagram | `/instagram/` | 2024-04-07 | 2024-04-07 | 31 |
| Newsletter | `/newsletter/` | 2024-03-27 | 2025-11-30 | 46,501 |
| Novel-Subscription | `/novel-subscription/` | 2025-02-25 | 2025-11-29 | 7,926 |
| Our Team | `/team/` | 2024-03-28 | 2025-11-23 | 29,934 |
| TikTok | `/tiktok/` | 2024-04-07 | 2024-04-07 | 49 |
| Youtube | `/youtube/` | 2024-04-07 | 2024-04-07 | 417 |

## Published blog posts recovered

| Post | Slug | Created | Modified | HTML length |
|---|---:|---:|---:|---:|
| First Blog Post for JSM Cooperative: Announcing "The Man in the Ballcap" | `first-blog-post-for-jsm-cooperative-announcing-the-man-in-the-ballcap` | 2023-12-05 | 2024-03-19 | 6,413 |
| El Hombre de La Gorra de Béisbol | `el-hombre-con-la-gorra` | 2023-12-26 | 2024-01-08 | 13,361 |
| Thanks from the JSM Cooperative | `thanks-from-the-jsm-cooperative` | 2023-12-26 | 2024-01-03 | 4,822 |
| Embracing the Journey | `embracing-the-journey` | 2024-01-03 | 2024-01-03 | 4,441 |
| 🌟 Unveiling Mysteries &amp; Making a Difference: Join the Adventure with The Man in the Ballcap 📚✨ | `%f0%9f%8c%9f-unveiling-mysteries-making-a-difference-join-the-adventure-with-the-man-in-the-ballcap-%f0%9f%93%9a%e2%9c%a8` | 2024-02-22 | 2024-02-22 | 4,453 |
| Turning Pages, Making Changes: JSM Cooperative's Leap to Tax-Exempt Status | `turning-pages-making-changes-jsm-cooperatives-leap-to-tax-exempt-status` | 2024-03-19 | 2024-03-22 | 4,548 |
| Marching Together: The Power of Community in the Fight Against Alzheimer's | `marching-together-the-power-of-community-in-the-fight-against-alzheimers` | 2024-03-23 | 2024-04-01 | 7,483 |
| Empowering Change: How Every Book Purchase Fuels Our Mission | `empowering-change-how-every-book-purchase-fuels-our-mission` | 2024-04-04 | 2024-04-04 | 4,654 |
| The Man in the Ballcap Goes Spanish: A New Chapter in Our Journey | `the-man-in-the-ballcap-goes-spanish-a-new-chapter-in-our-journey` | 2024-05-01 | 2024-05-01 | 172,620 |

## Flask coverage decisions

The recovered WordPress export contains 10 published pages. This updated Flask build now includes routes/templates or redirects for all 10:

- `/blogs/` → Flask blog index + imported WordPress posts as Markdown/HTML files.
- `/chapter-readings/` → new chapter readings/book page.
- `/contactus/` → redirect/alias to `/contact/`.
- `/donate/` → redesigned neon Camino donation page.
- `/instagram/`, `/tiktok/`, `/youtube/` → social landing routes.
- `/newsletter/` → new full Newsletter page using local signup + optional Mailchimp action URL.
- `/novel-subscription/` → new Camino subscription page.
- `/team/` → new Our Team page.

Raw WordPress HTML for each recovered page/post is preserved under `wordpress_export/pages_raw/` and `wordpress_export/posts_raw/`.

