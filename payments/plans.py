from decimal import Decimal


APPLICATION_FREE_LIMIT = 5


TEACHER_PREMIUM_PLANS = [
    {
        "id": "premium",
        "name": "Premium",
        "tagline": "Unlimited gig applications and stronger tutor visibility.",
        "monthly_amount": Decimal("149"),
        "yearly_amount": Decimal("1490"),
        "yearly_discount_percent": 17,
        "popular": True,
        "features": [
            "Unlimited gig applications",
            "Premium badge on your tutor profile",
            "Higher placement than free teachers",
            "Priority placement in tutor lists",
            "Featured badge on applications",
            "Performance stats in your teacher dashboard",
        ],
    },
]


GIG_BOOST_PLANS = [
    {
        "id": "spotlight",
        "name": "Spotlight",
        "amount": Decimal("499"),
        "duration_days": 7,
        "popular": False,
        "features": [
            "Boosted placement for 7 days",
            "Highlighted gig label",
            "More visibility to verified teachers",
        ],
    },
    {
        "id": "priority",
        "name": "Priority",
        "amount": Decimal("899"),
        "duration_days": 14,
        "popular": True,
        "features": [
            "Boosted placement for 14 days",
            "Priority highlight in gig lists",
            "Better exposure during teacher browsing",
        ],
    },
    {
        "id": "max_reach",
        "name": "Max Reach",
        "amount": Decimal("1499"),
        "duration_days": 30,
        "popular": False,
        "features": [
            "Boosted placement for 30 days",
            "Highest boost weight",
            "Best fit for urgent tutoring needs",
        ],
    },
]


def serialize_money(value):
    return int(value) if value == value.to_integral_value() else float(value)


def teacher_plan_options():
    plans = []
    for plan in TEACHER_PREMIUM_PLANS:
        monthly_amount = plan["monthly_amount"]
        yearly_amount = plan["yearly_amount"]
        yearly_full_price = monthly_amount * Decimal("12")
        yearly_savings = yearly_full_price - yearly_amount

        for billing_cycle, amount, duration_days, savings in [
            ("monthly", monthly_amount, 30, Decimal("0")),
            ("yearly", yearly_amount, 365, yearly_savings),
        ]:
            plans.append(
                {
                    "id": f"{plan['id']}_{billing_cycle}",
                    "plan_id": plan["id"],
                    "billing_cycle": billing_cycle,
                    "name": plan["name"],
                    "tagline": plan["tagline"],
                    "duration_days": duration_days,
                    "amount": serialize_money(amount),
                    "currency": "NPR",
                    "savings": serialize_money(savings) if savings > 0 else None,
                    "discount_percent": plan["yearly_discount_percent"]
                    if billing_cycle == "yearly"
                    else 0,
                    "popular": plan["popular"] and billing_cycle == "yearly",
                    "features": plan["features"],
                }
            )

    return plans


def find_teacher_plan(option_id):
    return next((plan for plan in teacher_plan_options() if plan["id"] == option_id), None)


def boost_plan_options():
    return [
        {
            **plan,
            "amount": serialize_money(plan["amount"]),
            "currency": "NPR",
        }
        for plan in GIG_BOOST_PLANS
    ]


def find_boost_plan(plan_id):
    return next((plan for plan in boost_plan_options() if plan["id"] == plan_id), None)
