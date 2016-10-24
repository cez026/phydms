"""Tests `phydmslib.treelikelihood.TreeLikelihood`.

Written by Jesse Bloom.
"""

import os
import sys
import re
import math
import unittest
import random
import copy
import scipy
import matplotlib
matplotlib.use('pdf')
import matplotlib.pyplot as plt
import Bio.Phylo
import phydmslib.treelikelihood
from phydmslib.constants import *


class test_TreeLikelihood(unittest.TestCase):
    """Tests `phydmslib.treelikelihood.TreeLikelihood` class."""

    def setUp(self):
        """Set up parameters for test."""
        random.seed(1)
        scipy.random.seed(1)

        # define tree and write image to a file
        self.newick = ('(($node_1=CAACAT$:0.1,$node_2=CAGCAG$:0.15)'
                       '$node_4=x$:0.15,$node_3=GAAAAG$:0.25)$node_5=y$:0.02;')
        tempfile = '_temp.tree'
        with open(tempfile, 'w') as f:
            f.write(self.newick)
        self.tree = Bio.Phylo.read(tempfile, 'newick')
        os.remove(tempfile)
        branch_labels = {} # branch annotations
        self.brlen = {}
        cladebyname = dict([(clade.name, clade) for clade in 
                self.tree.find_clades()])
        for (name, brlen) in re.findall(
                '(?P<name>\$node_\d\=[A-z]+\$)\:(?P<brlen>\d+\.\d+)', 
                self.newick):
            if name != self.tree.root.name:
                i = name.split('=')[0][-1] # node number
                branch_labels[cladebyname[name]] = "$t_{0}={1}$".format(
                        i, brlen)
                self.brlen[int(i)] = float(brlen)
        matplotlib.rc('text', usetex=True)
        Bio.Phylo.draw(self.tree, do_show=False, branch_labels=branch_labels)
        plt.axis('off')
        plt.savefig('test_treelikelihood_image.pdf')

        # define alignment
        self.nseqs = self.tree.count_terminals()
        self.nsites = 2
        self.alignment = []
        self.codons = {} # indexed by node, site, gives codon index
        for node in self.tree.get_terminals():
            seq = node.name.split('=')[1][ : -1]
            i = int(node.name.split('=')[0][-1]) # node number
            self.codons[i] = {}
            assert len(seq) == 3 * self.nsites
            self.alignment.append((node.name, seq))
            for r in range(self.nsites):
                codon = seq[3 * r : 3 * r + 3]
                self.codons[i][r] = CODON_TO_INDEX[codon]
        assert len(self.alignment) == self.nseqs

        # define model
        self.prefs = []
        minpref = 0.02
        for r in range(self.nsites):
            rprefs = scipy.random.dirichlet([0.5] * N_AA)
            rprefs[rprefs < minpref] = minpref
            rprefs /= rprefs.sum()
            self.prefs.append(dict(zip(sorted(AA_TO_INDEX.keys()), rprefs)))
        self.model = phydmslib.models.ExpCM(self.prefs)

    def test_InitializeTreeLikelihood(self):
        """Test that `TreeLikelihood` initializes properly."""
        tl = phydmslib.treelikelihood.TreeLikelihood(self.tree, self.alignment,
                self.model)
        self.assertTrue(tl.nsites == self.nsites)
        self.assertTrue(tl.nseqs == self.nseqs)
        self.assertTrue(tl.nnodes == len(tl.internalnodes) + self.nseqs)
        self.assertTrue(all([t > 0 for t in tl.t]))
        for n in tl.internalnodes:
            for descend in [tl.rdescend, tl.ldescend]:
                self.assertTrue(0 <= descend[n] < n, "{0}, {1}".format(n, descend[n]))

    def test_TreeLikelihood_paramsarray(self):
        """Tests `TreeLikelihood` params array setting and getting."""
        random.seed(1)
        scipy.random.seed(1)
        model = copy.deepcopy(self.model)
        modelparams = {
                'eta':scipy.random.dirichlet([5] * (N_NT - 1)),
                'mu':random.uniform(0.2, 2.0),
                'beta':random.uniform(0.8, 1.6),
                'kappa':random.uniform(0.5, 5.0),
                'omega':random.uniform(0.1, 2),
                }
        model.updateParams(modelparams)
        tl = phydmslib.treelikelihood.TreeLikelihood(self.tree,
                self.alignment, model)
        logl = tl.loglik
        paramsarray = tl.paramsarray
        nparams = len(paramsarray)
        self.assertTrue(nparams == sum(map(lambda x: (1 if isinstance(x, float)
                else len(x)), modelparams.values())))
        # set to new value, make sure TreeLikelihood attributes have changed
        tl.paramsarray = scipy.array([random.uniform(0.2, 0.8) for i in 
                range(nparams)])
        for (param, value) in modelparams.items():
            self.assertFalse(scipy.allclose(value, getattr(tl.model, param)))
        self.assertFalse(scipy.allclose(logl, tl.loglik))
        # re-set to old value, make sure attributes return to original values
        tl.paramsarray = copy.deepcopy(paramsarray)
        self.assertTrue(scipy.allclose(logl, tl.loglik))
        for (param, value) in modelparams.items():
            self.assertTrue(scipy.allclose(value, getattr(tl.model, param)))

    def test_Likelihood(self):
        """Tests likelihood of `TreeLikelihood` object."""
        mus = [0.5, 1.5]
        partials_by_mu = {}
        siteloglik_by_mu = {}
        loglik_by_mu = {}
        for mu in mus:
            model = copy.deepcopy(self.model)
            model.updateParams({'mu':mu})
            tl = phydmslib.treelikelihood.TreeLikelihood(self.tree,
                    self.alignment, model)
            # Here we are doing the multiplication hand-coded for the
            # tree defined in `setUp`. This calculation would be wrong
            # if the tree in `setUp` were to be changed.
            M = {}
            for (node, t) in self.brlen.items():
                M[node] = model.M(t)
            # compute partials at root node
            partials = scipy.zeros(shape=(self.nsites, N_CODON))
            siteloglik = scipy.zeros(shape=(self.nsites,))
            loglik = 0.0
            for r in range(self.nsites):
                for y in range(N_CODON):
                    for x in range(N_CODON):
                        partials[r][y] += (M[3][r][y][self.codons[3][r]] *
                                M[4][r][y][x] * M[1][r][x][self.codons[1][r]]
                                * M[2][r][x][self.codons[2][r]])
                    siteloglik[r] += partials[r][y] * model.stationarystate[r, y]
                siteloglik[r] = math.log(siteloglik[r])
                loglik += siteloglik[r]
            partials_by_mu[mu] = {'actual':tl.L[-1], 'expected':partials}
            siteloglik_by_mu[mu] = {'actual':tl.siteloglik, 'expected':siteloglik}
            loglik_by_mu[mu] = {'actual':tl.loglik, 'expected':loglik}

        for (i, mu1) in enumerate(mus):
            for (name, d) in [('partials', partials_by_mu),
                                      ('siteloglik', siteloglik_by_mu),
                                      ('loglik', loglik_by_mu)]:
                self.assertTrue(scipy.allclose(d[mu1]['actual'],
                        d[mu1]['expected']), "Mismatch: {0}".format(name))
                for mu2 in mus[i + 1 : ]:
                    self.assertFalse(scipy.allclose(d[mu1]['actual'],
                            d[mu2]['actual']), "Bad match: {0}".format(name))

    def test_LikelihoodDerivativesModelParams(self):
        """Test derivatives of `TreeLikelihood` with respect to model params."""
        tl = phydmslib.treelikelihood.TreeLikelihood(self.tree,
                    self.alignment, copy.deepcopy(self.model))
        for itest in range(2):
            random.seed(itest)
            scipy.random.seed(itest)
            modelparams = {
                    'eta':scipy.random.dirichlet([5] * (N_NT - 1)),
                    'mu':random.uniform(0.2, 2.0),
                    'beta':random.uniform(0.8, 1.6),
                    'kappa':random.uniform(0.5, 5.0),
                    'omega':random.uniform(0.1, 2),
                    }
            tl.updateParams(modelparams)



if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    unittest.main(testRunner=runner)
