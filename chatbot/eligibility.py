"""
Eligibility checker for HPV vaccination in India.

This module provides rule-based logic to determine HPV vaccine eligibility
based on MoHFW / WHO / ICMR guidelines for India.
"""

from dataclasses import dataclass
from enum import Enum


class Gender(str, Enum):
    FEMALE = "Female"
    MALE = "Male"
    OTHER = "Other / Prefer not to say"


@dataclass
class EligibilityResult:
    eligible: bool
    recommendation: str
    dose_schedule: str
    notes: list[str]


def check_eligibility(
    age: int,
    gender: str,
    already_vaccinated: bool,
    is_pregnant: bool,
) -> EligibilityResult:
    """
    Determine HPV vaccine eligibility based on MoHFW/WHO/ICMR guidelines for India.

    Args:
        age: Age of the person in years.
        gender: Gender of the person ('Female', 'Male', or 'Other / Prefer not to say').
        already_vaccinated: Whether the person has already completed HPV vaccination.
        is_pregnant: Whether the person is currently pregnant.

    Returns:
        EligibilityResult with eligibility status, recommendation, dose schedule, and notes.
    """
    notes: list[str] = []

    # Already vaccinated
    if already_vaccinated:
        return EligibilityResult(
            eligible=False,
            recommendation="You have already completed HPV vaccination. No further doses are needed.",
            dose_schedule="N/A",
            notes=["Continue with routine cervical cancer screening as recommended by your doctor."],
        )

    # Pregnancy: vaccination not recommended
    if is_pregnant:
        return EligibilityResult(
            eligible=False,
            recommendation=(
                "HPV vaccination is not recommended during pregnancy. "
                "Please complete your vaccination after delivery."
            ),
            dose_schedule="N/A",
            notes=[
                "Breastfeeding women may receive the HPV vaccine.",
                "Consult your healthcare provider after delivery to plan vaccination.",
            ],
        )

    # Age below 9: not recommended
    if age < 9:
        return EligibilityResult(
            eligible=False,
            recommendation="HPV vaccination is not recommended for children under 9 years of age.",
            dose_schedule="N/A",
            notes=["Revisit vaccination eligibility when the child turns 9."],
        )

    # Primary target: 9–14 years
    if 9 <= age <= 14:
        dose_schedule = "2 doses: Dose 1 now, Dose 2 at 6 months after Dose 1."
        recommendation = (
            "You are in the primary target age group (9–14 years) for HPV vaccination in India. "
            "Vaccination is highly recommended and available free under the government UIP programme."
        )
        notes = [
            "The 2-dose schedule is approved for this age group.",
            "The indigenously developed Cervavac vaccine is available at government health facilities.",
        ]
        return EligibilityResult(eligible=True, recommendation=recommendation, dose_schedule=dose_schedule, notes=notes)

    # Secondary target: 15–26 years
    if 15 <= age <= 26:
        dose_schedule = "3 doses: Dose 1 now, Dose 2 at 1–2 months, Dose 3 at 6 months."
        recommendation = (
            "You are in the recommended age group (15–26 years) for HPV vaccination. "
            "Vaccination is recommended even if you have been sexually active."
        )
        notes = [
            "A 3-dose schedule is required for this age group.",
            "Vaccination still provides protection against HPV types you have not yet been exposed to.",
        ]
        if gender == Gender.FEMALE.value:
            notes.append(
                "Continue regular cervical cancer screening (Pap smear or HPV DNA test) regardless of vaccination."
            )
        return EligibilityResult(eligible=True, recommendation=recommendation, dose_schedule=dose_schedule, notes=notes)

    # 27–45 years: may benefit, recommend consulting a doctor
    if 27 <= age <= 45:
        dose_schedule = "3 doses: Dose 1 now, Dose 2 at 1–2 months, Dose 3 at 6 months (if advised by doctor)."
        recommendation = (
            "HPV vaccination may still be beneficial for individuals aged 27–45 years, "
            "though the benefit decreases with age. Consult your healthcare provider to decide."
        )
        notes = [
            "Benefit depends on prior HPV exposure history.",
            "A doctor's consultation is strongly recommended before vaccination at this age.",
        ]
        if gender == Gender.FEMALE.value:
            notes.append(
                "Regular cervical cancer screening is especially important for this age group."
            )
        return EligibilityResult(eligible=True, recommendation=recommendation, dose_schedule=dose_schedule, notes=notes)

    # Above 45: generally not recommended, but individual assessment possible
    return EligibilityResult(
        eligible=False,
        recommendation=(
            "HPV vaccination is generally not recommended for individuals above 45 years. "
            "Please consult your healthcare provider for personalised advice."
        ),
        dose_schedule="N/A",
        notes=[
            "Regular cancer screening is important for this age group.",
            "Consult your doctor for personalised health guidance.",
        ],
    )


def render_eligibility_checker() -> None:
    """
    Render the Eligibility Checker UI using Streamlit.
    Must be called within a Streamlit app context.
    """
    import streamlit as st

    st.subheader("💉 HPV Vaccine Eligibility Checker")
    st.markdown(
        "Answer the questions below to find out whether you or someone you know may be eligible for "
        "the HPV vaccine in India. _This is for informational purposes only and is not a substitute "
        "for professional medical advice._"
    )

    with st.form("eligibility_form"):
        age = st.number_input("Age (in years)", min_value=1, max_value=120, value=12, step=1)
        gender = st.selectbox("Gender", options=[g.value for g in Gender])
        already_vaccinated = st.radio(
            "Have you already completed HPV vaccination?",
            options=["No", "Yes"],
            index=0,
        )
        is_pregnant = st.radio(
            "Are you currently pregnant? (if applicable)",
            options=["No", "Yes"],
            index=0,
        )
        submitted = st.form_submit_button("Check Eligibility")

    if submitted:
        result = check_eligibility(
            age=int(age),
            gender=gender,
            already_vaccinated=(already_vaccinated == "Yes"),
            is_pregnant=(is_pregnant == "Yes"),
        )

        if result.eligible:
            st.success(f"✅ **Eligible for HPV Vaccination**\n\n{result.recommendation}")
        else:
            st.warning(f"ℹ️ **{result.recommendation}**")

        st.markdown(f"**Recommended Dose Schedule:** {result.dose_schedule}")

        if result.notes:
            st.markdown("**Additional Notes:**")
            for note in result.notes:
                st.markdown(f"- {note}")

        st.caption(
            "⚕️ Always consult a qualified healthcare provider before making vaccination decisions."
        )
