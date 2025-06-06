import pathlib
import numpy as np
import pandas as pd
from typing import Union, Tuple


class QuestionnaireAnalysis:
    """
    Reads and analyzes data generated by the questionnaire experiment.
    Should be able to accept strings and pathlib.Path objects.
    """

    def __init__(self, data_fname: Union[pathlib.Path, str]):
        if isinstance(data_fname, str):
            data_fname = pathlib.Path(data_fname)
        elif not isinstance(data_fname, pathlib.Path):
            raise TypeError("data_fname must be a string or a pathlib.Path object.")
        if not data_fname.exists():
            raise ValueError(f"File {data_fname} does not exist.")

        self.data_fname = data_fname
        self.data = None

    def read_data(self):
        """Reads the json data located in self.data_fname into memory, to
        the attribute self.data.
        """
        self.data = pd.read_json(self.data_fname)


    def show_age_distrib(self) -> Tuple[np.ndarray, np.ndarray]:
        """Calculates and plots the age distribution of the participants.

    Returns
    -------
    hist : np.ndarray
      Number of people in a given bin
    bins : np.ndarray
      Bin edges
        """
        hist, edges = np.histogram(self.data["age"], bins=np.arange(0, 101, 10))
        return hist, edges

    def remove_rows_without_mail(self) -> pd.DataFrame:
        """Checks self.data for rows with invalid emails, and removes them.

    Returns
    -------
    df : pd.DataFrame
      A corrected DataFrame, i.e. the same table but with the erroneous rows removed and
      the (ordinal) index after a reset.
        """

        valid_emails = self.data['email'].apply(self.is_valid_email)
        corrected_df = self.data[valid_emails].reset_index(drop=True)
        return corrected_df

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """
        Checks if the given email address is valid according to the specified rules:
        A valid email address is one that follows these conditions:
        Contains exactly one "@" sign, but doesn't start or end with it.
        Contains a "." sign, but doesn't start or end with it.
        The letter following the "@" sign (i.e, appears after it) must not be "." .
        :param email: str
        :return: True if the email is valid, False otherwise.
        """
        if not isinstance(email, str):
            return False
        if email.count('@') != 1 or email.startswith('@') or email.endswith('@'):
            return False
        if '.' not in email or email.startswith('.') or email.endswith('.'):
            return False
        at_index = email.index('@')
        if email[at_index + 1] == '.':
            return False

        return True

    def fill_na_with_mean(self) -> Tuple[pd.DataFrame, np.ndarray]:
        """Finds, in the original DataFrame, the subjects that didn't answer
        all questions, and replaces that missing value with the mean of the
        other grades for that student.

    Returns
    -------
    df : pd.DataFrame
      The corrected DataFrame after insertion of the mean grade
    arr : np.ndarray
          Row indices of the students that their new grades were generated
        """
        df = self.data.copy()
        questions_columns = ["q1", "q2", "q3", "q4", "q5"]
        rows_with_na = df[questions_columns].isna().any(axis=1)
        # Get their integer indices as a numpy array
        rows_indices = np.where(rows_with_na)[0]

        for idx in rows_indices:
            row = df.loc[idx, questions_columns]
            mean_value = row.mean(skipna=True)
            df.loc[idx, questions_columns] = row.fillna(mean_value)

        return df, rows_indices

    def score_subjects(self, maximal_nans_per_sub: int = 1) -> pd.DataFrame:
        """Calculates the average score of a subject and adds a new "score" column
        with it.

        If the subject has more than "maximal_nans_per_sub" NaN in his grades, the
        score should be NA. Otherwise, the score is simply the mean of the other grades.
        The datatype of score is UInt8, and the floating point raw numbers should be
        rounded down.

        Parameters
        ----------
        maximal_nans_per_sub : int, optional
            Number of allowed NaNs per subject before giving a NA score.

        Returns
        -------
        pd.DataFrame
            A new DF with a new column - "score".
        """

        df = self.data.copy()
        questions_columns = ["q1", "q2", "q3", "q4", "q5"]

        nans_count = df[questions_columns].isna().sum(axis=1)
        mean_scores = df[questions_columns].mean(axis=1, skipna=True)

        score = pd.Series(pd.NA, index=df.index, dtype="UInt8")

        # find and keep rows with NaNs less than or equal to maximal_nans_per_sub
        eligible_mask = (nans_count <= maximal_nans_per_sub)
        score.loc[eligible_mask] = np.floor(mean_scores[eligible_mask]).astype("UInt8")

        df["score"] = score

        return df

    def correlate_gender_age(self) -> pd.DataFrame:
        """Looks for a correlation between the gender of the subject, their age
        and the score for all five questions.

    Returns
    -------
    pd.DataFrame
        A DataFrame with a MultiIndex containing the gender and whether the subject is above
        40 years of age, and the average score in each of the five questions.
    """

        df = self.data.copy()
        questions_columns = ["q1", "q2", "q3", "q4", "q5"]

        # Drop any participant whose age is NaN so they don't end up in “<= 40” group
        df = df[df['age'].notna()]
        df["above_40"] = df["age"] > 40

        df = df.set_index(["gender", "age"], append=True)


        grouped = df.groupby(["gender", "above_40"])[questions_columns].mean()
        grouped.index.set_names(["gender", "age"], inplace=True)

        return grouped