# MonoRaceGate

Drone Racing Gate Dataset with Precise Corner Labels

<img width="640" height="360" alt="img_106" src="https://github.com/user-attachments/assets/f18e2583-9d08-4081-b59a-dcc20daa0f6d" />


## Installation

Create and activate the conda environment:

```bash
conda env create -f environment.yml
conda activate monoracegate
```

Then download the data and generate masks:

```bash
make
```


## Labels

 - ```corner.csv``` files contain the ```x``` and ```y``` coordinates of the inner gate corners in the sequence: Top-Left, Top-Right, Bottom-Right, Bottom-Left.



 ## Usage

 Free to use. Please refer to the corresponding paper:


 ```bibtex
@article{bahnam2026monorace,
  author  = {Stavrow A. Bahnam and Robin Ferede and Till M. Blaha and Anton E. Lang and Erin Lucassen and Quentin Missinne and Aderik E. C. Verraest and Christophe De Wagter and Guido C. H. E. de Croon},
  title   = {MonoRace: Robust monocular AI for champion-level drone racing},
  journal = {Science Robotics},
  volume  = {11},
  number  = {119},
  pages   = {eaee9250},
  year    = {2026},
  doi     = {10.1126/scirobotics.aee9250},
}
```

Preprint: [arXiv:2601.15222](https://arxiv.org/abs/2601.15222)

