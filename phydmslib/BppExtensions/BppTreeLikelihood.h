/* BppTreeLikelihood.h

   Defines a C++ class that interfaces with Bio++
   to define a tree, model, and likelihood calculation object.
   This class comprehensively performs all of the operations
   needed to interface with Bio++.

   Written by Jesse Bloom
*/

#include <string>
#include <vector>
#include <Bpp/Seq/Alphabet/NucleicAlphabet.h>
#include <Bpp/Seq/Alphabet/DNA.h>
#include <Bpp/Seq/Alphabet/Alphabet.h>
#include <Bpp/Seq/Alphabet/CodonAlphabet.h>
#include <Bpp/Seq/GeneticCode/GeneticCode.h>
#include <Bpp/Seq/GeneticCode/StandardGeneticCode.h>
#include <Bpp/Seq/Container/VectorSiteContainer.h>
#include <Bpp/Seq/Container/SiteContainerTools.h>
#include <Bpp/Seq/Sequence.h>
#include <Bpp/Phyl/App/PhylogeneticsApplicationTools.h>
#include <Bpp/Phyl/Io/IoTree.h>
#include <Bpp/Phyl/Io/Newick.h>
#include <Bpp/Phyl/Model/RateDistribution/ConstantRateDistribution.h>
#include <Bpp/Phyl/Likelihood/DiscreteRatesAcrossSitesTreeLikelihood.h>
#include <Bpp/Phyl/Likelihood/NNIHomogeneousTreeLikelihood.h>
#include <Bpp/Phyl/Likelihood/RHomogeneousTreeLikelihood.h>
#include <Bpp/Phyl/Likelihood/RHomogeneousMixedTreeLikelihood.h>
#include <Bpp/Phyl/NewLikelihood/SequenceEvolution.h>
#include <Bpp/Phyl/NewLikelihood/PhyloLikelihood.h>
#include <Bpp/Phyl/NewLikelihood/PartitionSequenceEvolution.h>
#include <Bpp/Phyl/NewLikelihood/PartitionPhyloLikelihood.h>

namespace bppextensions {

    /**
     *@brief Interface between bpp and the Python cython wrapper, defined as class that does all likelihood computations.
     *
     * You initialize an object of this class with the sequences, initial tree, substitution model, and various
     * other relevant options. The object then can be manipulated via the interface defined here for all necessary
     * operations.
     */
    class BppTreeLikelihood {

        public:
            /**
             *@brief Constructor
             *
             *@param seqnames A vector of strings giving the sequence names
             *
             *@param seqs A vector of strings giving the sequences (should all be aligned, no stop codons)
             *
             *@param treefile Name of an existing file giving Newick tree with names matching those in seqnames
             *
             *@param modelstring A string defining the model. See the Python wrapper for list of valid values.
             *
             * @param infertopology Do we infer the tree topology by maximum likelihood? 
             *
             * @param preferences Site-specific amino-acid preferences, keyed by integer site (1, 2, ... numbering), then maps keyed by codon and values preference. Value does not matter if modelstring is not "ExpCM".
             *
             * @param fixpreferences Do we fix the preferences or treat them as free parameters (only matters if modelstring is "ExpCM").
             *
             * @param oldlikelihoodmethod Do we use the old Bpp likelihood method rather then the NewLikelihood? Only can be used for non-partitioned data.
             * 
             * @param omegabysite Do we fit a different value of omega for each site (done if true) or use the same value for all sites? 
             * 
             * @param fixbrlen Do we fix the branch lengths?
             *
             * @param recursion Recursion method used for likelihood. Can be "S" for simple or "D" for double.
             * 
             */
            BppTreeLikelihood(std::vector<std::string> seqnames, std::vector<std::string> seqs, std::string treefile, std::string modelstring, int infertopology, std::map<int, std::map<std::string, double> > preferences, int fixpreferences, int oldlikelihoodmethod, int omegabysite, int fixbrlen, char recursion);

            /**
             *@brief Destructor
             */
            ~BppTreeLikelihood();

            /**
             *@return returns number of sequences
             */
            long NSeqs();

            /**
             *@return returns number of sites
             */
            long NSites();

            /**
             *@brief Writes the current Newick tree to a file

             *@param fname Name of file to which we write the tree
             */
            void NewickTree(std::string fname); 
            
            /**
             *@return Returns current log likelihood
             */
            double LogLikelihood(); 

            /**
             *@brief Optimizes the object by maximum likelihood. May optimize topology, branches, and model parameters depending on how object was initialized.
             */
            void OptimizeLikelihood(); 

            /**
             *@brief Gets current values of model parameters.
             *
             *@return map keyed by parameter names, values current values
             *
             */
            std::map<std::string, double> ModelParams(); 

            /**
             *@brief Returns current stationary state of substitition model for a site
             *
             *@param isite the site for which we get the stationary state in 1, 2, ..., NSites() numbering
             *
             *@return map keyed by codons, values are stationary state
             */
            std::map<std::string, double> StationaryState(long isite);

            /**
             *@brief Returns parameters currently being ignored for optimization
             *
             *@return a comma-delimited string of the parameters being ignore, which may include wildcards indicated by *
             *
             */
            std::string OptimizationIgnoredParameters();

        private:
            bool verbose; // verbosity of Bpp functions
            bool oldlikmethod;
            std::map<std::string, std::string> optimizationparams; // specifies parameters for optimization
            bpp::NucleicAlphabet *ntalphabet;
            bpp::CodonAlphabet *alphabet;
            bpp::GeneticCode *gcode;
            bpp::VectorSiteContainer *sites;
            bpp::Tree *tree;
            bpp::Newick *treeReaderWriter;
            std::map<size_t, bpp::SubstitutionModel*> models;
            bpp::DiscreteDistribution *ratedistribution;
            bpp::SubstitutionProcessCollection *substitutionprocesscollection;
            bpp::SequenceEvolution *sequenceevolution;
            bpp::PhyloLikelihood *phylolikelihood;
            bpp::DiscreteRatesAcrossSitesTreeLikelihood *oldtreelikelihood;
            size_t sharedmodelindex;
            std::map<std::string, std::string> constrainedparams; // keyed by param, value is what it is constrained to
    };
};
